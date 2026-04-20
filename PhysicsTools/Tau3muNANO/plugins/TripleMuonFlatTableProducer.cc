#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/stream/EDProducer.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Framework/interface/ESHandle.h"
#include "FWCore/Framework/interface/EventSetup.h"

#include "DataFormats/Candidate/interface/CompositeCandidate.h"
#include "DataFormats/PatCandidates/interface/Muon.h"
#include "DataFormats/NanoAOD/interface/FlatTable.h"

#include "TrackingTools/TransientTrack/interface/TransientTrackBuilder.h"
#include "TrackingTools/Records/interface/TransientTrackRecord.h"
#include "RecoVertex/KalmanVertexFit/interface/KalmanVertexFitter.h"
#include "CommonTools/Statistics/interface/ChiSquaredProbability.h"

#include <vector>
#include <string>

class TripleMuonFlatTableProducer : public edm::stream::EDProducer<> {
public:
    explicit TripleMuonFlatTableProducer(const edm::ParameterSet& iConfig) :
        srcToken_(consumes<edm::View<reco::CompositeCandidate>>(iConfig.getParameter<edm::InputTag>("src"))),
        tableName_(iConfig.getParameter<std::string>("name")),
        doc_(iConfig.getParameter<std::string>("doc")),
        // DICHIARAZIONE DEL TOKEN (Nuovo standard CMSSW)
        ttbToken_(esConsumes<TransientTrackBuilder, TransientTrackRecord>(edm::ESInputTag("", "TransientTrackBuilder"))) {
        produces<nanoaod::FlatTable>();
    }

    void produce(edm::Event& iEvent, const edm::EventSetup& iSetup) override {
        edm::Handle<edm::View<reco::CompositeCandidate>> src;
        iEvent.getByToken(srcToken_, src);

        // ACCESSO TRAMITE TOKEN
        auto const& ttBuilder = iSetup.getData(ttbToken_);

        size_t nSize = src.isValid() ? src->size() : 0;

        std::vector<float> pt, eta, phi, mass;
        std::vector<int> charge;
        std::vector<float> vtx_prob, vtx_chi2, vtx_x, vtx_y, vtx_z;
        std::vector<float> mu1_pt, mu2_pt, mu3_pt;
        std::vector<float> mu1_eta, mu2_eta, mu3_eta;
        std::vector<float> mu1_phi, mu2_phi, mu3_phi;
        std::vector<float> mu1_energy, mu2_energy, mu3_energy;
        std::vector<int> mu1_charge, mu2_charge, mu3_charge;

        // Dati Muoni (Inclusi ID)
        std::vector<int> mu1_isGlobal, mu1_isMedium;
        std::vector<int> mu2_isGlobal, mu2_isMedium;
        std::vector<int> mu3_isGlobal, mu3_isMedium;

        if (nSize > 0) {
            for (const auto& obj : *src) {
                pt.push_back(obj.pt());
                eta.push_back(obj.eta());
                phi.push_back(obj.phi());
                mass.push_back(obj.mass());
                charge.push_back(obj.charge());

                unsigned int nDau = obj.numberOfDaughters();
                mu1_pt.push_back(nDau > 0 ? obj.daughter(0)->pt() : -1.0);
                mu2_pt.push_back(nDau > 1 ? obj.daughter(1)->pt() : -1.0);
                mu3_pt.push_back(nDau > 2 ? obj.daughter(2)->pt() : -1.0);

                mu1_eta.push_back(nDau > 0 ? obj.daughter(0)->eta() : -1.0);
                mu2_eta.push_back(nDau > 1 ? obj.daughter(1)->eta() : -1.0);
                mu3_eta.push_back(nDau > 2 ? obj.daughter(2)->eta() : -1.0);

                mu1_phi.push_back(nDau > 0 ? obj.daughter(0)->phi() : -1.0);
                mu2_phi.push_back(nDau > 1 ? obj.daughter(1)->phi() : -1.0);
                mu3_phi.push_back(nDau > 2 ? obj.daughter(2)->phi() : -1.0);

                mu1_energy.push_back(nDau > 0 ? obj.daughter(0)->energy() : -1.0);
                mu2_energy.push_back(nDau > 1 ? obj.daughter(1)->energy() : -1.0);
                mu3_energy.push_back(nDau > 2 ? obj.daughter(2)->energy() : -1.0);

                mu1_charge.push_back(nDau > 0 ? obj.daughter(0)->charge() : -1.0);
                mu2_charge.push_back(nDau > 1 ? obj.daughter(1)->charge() : -1.0);
                mu3_charge.push_back(nDau > 2 ? obj.daughter(2)->charge() : -1.0);

                std::vector<reco::TransientTrack> ttrks;
                for (unsigned int j = 0; j < nDau; ++j) {
                    const reco::Candidate* dau = obj.daughter(j);
                    
                    // 1. Risaliamo al pat::Muon originale usando il Ptr alla sorgente
                    // Questo funziona se il tripletto è stato creato da slimmedMuons
                    const pat::Muon* mu = nullptr;
                    if (dau->sourceCandidatePtr(0).isNonnull()) {
                        mu = dynamic_cast<const pat::Muon*>(dau->sourceCandidatePtr(0).get());
                    }

                    int isG = 0;
                    int isM = 0;

                    if (mu) {
                        // 2. Se il cast ha avuto successo, leggiamo gli ID
                        isG = mu->isGlobalMuon() ? 1 : 0;
                        isM = muon::isMediumMuon(*mu) ? 1 : 0;
                        
                        // 3. Prendiamo la traccia per il fit del vertice
                        if (mu->bestTrack()) {
                            ttrks.push_back(ttBuilder.build(mu->bestTrack()));
                        }
                    } else {
                        // Fallback: se per qualche motivo non è un pat::Muon, 
                        // proviamo comunque a recuperare la traccia dal Candidate base
                        if (dau->bestTrack()) {
                            ttrks.push_back(ttBuilder.build(dau->bestTrack()));
                        }
                    }

                    // Assegnazione ai vettori per la tabella
                    if (j == 0) { mu1_isGlobal.push_back(isG); mu1_isMedium.push_back(isM); }
                    if (j == 1) { mu2_isGlobal.push_back(isG); mu2_isMedium.push_back(isM); }
                    if (j == 2) { mu3_isGlobal.push_back(isG); mu3_isMedium.push_back(isM); }
                }

                if (ttrks.size() == 3) {
                    KalmanVertexFitter kvf(true);
                    TransientVertex tv = kvf.vertex(ttrks);
                    if (tv.isValid()) {
                        vtx_chi2.push_back(tv.totalChiSquared());
                        vtx_prob.push_back(ChiSquaredProbability(tv.totalChiSquared(), tv.degreesOfFreedom()));
                        vtx_x.push_back(tv.position().x());
                        vtx_y.push_back(tv.position().y());
                        vtx_z.push_back(tv.position().z());
                    } else {
                        vtx_chi2.push_back(-1); vtx_prob.push_back(-1);
                        vtx_x.push_back(0); vtx_y.push_back(0); vtx_z.push_back(0);
                    }
                } else {
                    vtx_chi2.push_back(-1); vtx_prob.push_back(-1);
                    vtx_x.push_back(0); vtx_y.push_back(0); vtx_z.push_back(0);
                }
            }
        }

        auto table = std::make_unique<nanoaod::FlatTable>(nSize, tableName_, false, false);
        table->setDoc(doc_);
        table->addColumn<float>("pt", pt, "Pt of triplet", 12);
        table->addColumn<float>("mass", mass, "Mass of triplet", 14);
        table->addColumn<int>("charge", charge, "Charge of triplet");
        table->addColumn<float>("vtx_prob", vtx_prob, "Vertex prob", 10);
        table->addColumn<float>("vtx_chi2", vtx_chi2, "Vertex chi2", 10);
        table->addColumn<float>("vtx_x", vtx_x, "Vertex X", 10);
        table->addColumn<float>("vtx_y", vtx_y, "Vertex Y", 10);
        table->addColumn<float>("vtx_z", vtx_z, "Vertex Z", 10);
        table->addColumn<float>("mu1_pt", mu1_pt, "Mu1 pt", 10);
        table->addColumn<float>("mu2_pt", mu2_pt, "Mu2 pt", 10);
        table->addColumn<float>("mu3_pt", mu3_pt, "Mu3 pt", 10);
        table->addColumn<float>("mu1_eta", mu1_eta, "Mu1 eta", 10);
        table->addColumn<float>("mu2_eta", mu2_eta, "Mu2 eta", 10);
        table->addColumn<float>("mu3_eta", mu3_eta, "Mu3 eta", 10);
        table->addColumn<float>("mu1_phi", mu1_phi, "Mu1 phi", 10);
        table->addColumn<float>("mu2_phi", mu2_phi, "Mu2 phi", 10);
        table->addColumn<float>("mu3_phi", mu3_phi, "Mu3 phi", 10);
        table->addColumn<float>("mu1_charge", mu1_charge, "Mu1 charge", 10);
        table->addColumn<float>("mu2_charge", mu2_charge, "Mu2 charge", 10);
        table->addColumn<float>("mu3_charge", mu3_charge, "Mu3 charge", 10);
        table->addColumn<float>("mu1_energy", mu1_energy, "Mu1 energy", 10);
        table->addColumn<float>("mu2_energy", mu2_energy, "Mu2 energy", 10);
        table->addColumn<float>("mu3_energy", mu3_energy, "Mu3 energy", 10);
        table->addColumn<float>("mu1_isGlb", mu1_isGlobal, "Mu1 isGlobal", 10);
        table->addColumn<float>("mu2_isGlb", mu2_isGlobal, "Mu2 isGlobal", 10);
        table->addColumn<float>("mu3_isGlb", mu3_isGlobal, "Mu3 isGlobal", 10);
        table->addColumn<float>("mu1_isMdm", mu1_isMedium, "Mu1 isMedium", 10);
        table->addColumn<float>("mu2_isMdm", mu2_isMedium, "Mu2 isMedium", 10);
        table->addColumn<float>("mu3_isMdm", mu3_isMedium, "Mu3 isMedium", 10);

        iEvent.put(std::move(table));
    }

private:
    edm::EDGetTokenT<edm::View<reco::CompositeCandidate>> srcToken_;
    std::string tableName_;
    std::string doc_;
    // IL TOKEN DEVE ESSERE UN MEMBRO DELLA CLASSE
    edm::ESGetToken<TransientTrackBuilder, TransientTrackRecord> ttbToken_;
};

#include "FWCore/Framework/interface/MakerMacros.h"
DEFINE_FWK_MODULE(TripleMuonFlatTableProducer);