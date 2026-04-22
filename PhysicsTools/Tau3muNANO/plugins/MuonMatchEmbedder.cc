
#include <algorithm>
#include <limits>

#include "DataFormats/Common/interface/View.h"
#include "DataFormats/HepMCCandidate/interface/GenParticle.h"
#include "DataFormats/VertexReco/interface/Vertex.h"
#include "DataFormats/VertexReco/interface/VertexFwd.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/global/EDProducer.h"
#include "FWCore/ParameterSet/interface/ConfigurationDescriptions.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"
#include "FWCore/Utilities/interface/InputTag.h"
#include "TrackingTools/IPTools/interface/IPTools.h"
#include "TrackingTools/Records/interface/TransientTrackRecord.h"
#include "TrackingTools/TransientTrack/interface/TransientTrackBuilder.h"
#include "helper.h"

namespace {
  int getGenOrigin(const reco::GenParticleRef& gen) {
    if (gen.isNull()) return 0; // Nessun match a livello Gen

    const reco::Candidate* mother = gen->mother();
    bool foundPhi = false;
    bool foundDs = false;
    bool foundB = false;

    while (mother != nullptr) {
        int pdg = std::abs(mother->pdgId());
        
        // 1. Cerchiamo la Phi (333)
        if (pdg == 333) {
            foundPhi = true;
        }

        // 2. Cerchiamo la Ds (431)
        if (pdg == 431) {
            foundDs = true;
        }

        // 3. Cerchiamo un adrone B (5xx)
        if ((pdg / 100) == 5 || (pdg / 1000) == 5) {
            foundB = true;
            // Se troviamo un B, non serve risalire oltre nella gerarchia
            break; 
        }

        mother = mother->mother();
    }

    // --- Logica di classificazione finale ---
    
    // Se NON è passato per una Phi, è automaticamente "Other" (3)
    if (!foundPhi) return 3;

    // Se è passato per una Phi, controlliamo la provenienza della Phi:
    if (foundB) return 2;  // Non-Prompt (B -> ... -> Phi -> mu)
    if (foundDs) return 1; // Prompt (Ds -> Phi -> mu)

    // Phi prodotta in altri modi (es. frammentazione o decadimenti di adroni leggeri)
    return 3; 
  }
}

template <typename PATOBJ>
class MatchEmbedder : public edm::global::EDProducer<> {
  // perhaps we need better structure here (begin run etc)

public:
  explicit MatchEmbedder(const edm::ParameterSet &cfg)
      : src_{consumes<PATOBJCollection>(cfg.getParameter<edm::InputTag>("src"))},
        matching_{
            consumes<edm::Association<reco::GenParticleCollection> >(cfg.getParameter<edm::InputTag>("matching"))} {
    produces<PATOBJCollection>();
  }

  ~MatchEmbedder() override {}

  void produce(edm::StreamID, edm::Event &, const edm::EventSetup &) const override;

private:
  typedef std::vector<PATOBJ> PATOBJCollection;
  const edm::EDGetTokenT<PATOBJCollection> src_;
  const edm::EDGetTokenT<edm::Association<reco::GenParticleCollection> > matching_;
};

template <typename PATOBJ>
void MatchEmbedder<PATOBJ>::produce(edm::StreamID, edm::Event &evt, edm::EventSetup const &iSetup) const {
  // input
  edm::Handle<PATOBJCollection> src;
  evt.getByToken(src_, src);

  edm::Handle<edm::Association<reco::GenParticleCollection> > matching;
  evt.getByToken(matching_, matching);

  size_t nsrc = src->size();
  // output
  std::unique_ptr<PATOBJCollection> out(new PATOBJCollection());
  out->reserve(nsrc);

  for (unsigned int i = 0; i < nsrc; ++i) {
    edm::Ptr<PATOBJ> ptr(src, i);
    reco::GenParticleRef match = (*matching)[ptr];
    out->emplace_back(src->at(i));
    out->back().addUserInt("mcMatch", match.isNonnull() ? match->pdgId() : 0);
    out->back().addUserInt("genOrigin", getGenOrigin(match));
  }

  // adding label to be consistent with the muon and track naming
  evt.put(std::move(out));
}

#include "DataFormats/PatCandidates/interface/Muon.h"
typedef MatchEmbedder<pat::Muon> MuonMatchEmbedder;

#include "DataFormats/PatCandidates/interface/Electron.h"
typedef MatchEmbedder<pat::Electron> ElectronMatchEmbedder;

#include "DataFormats/PatCandidates/interface/CompositeCandidate.h"
typedef MatchEmbedder<pat::CompositeCandidate> CompositeCandidateMatchEmbedder;

#include "FWCore/Framework/interface/MakerMacros.h"
DEFINE_FWK_MODULE(MuonMatchEmbedder);
DEFINE_FWK_MODULE(ElectronMatchEmbedder);
DEFINE_FWK_MODULE(CompositeCandidateMatchEmbedder);