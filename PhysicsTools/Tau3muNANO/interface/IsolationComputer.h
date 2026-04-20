#ifndef IsolationComputer_h
#define IsolationComputer_h

#include "DataFormats/Math/interface/deltaR.h"

#include "DataFormats/Common/interface/Handle.h"
#include "DataFormats/PatCandidates/interface/PackedCandidate.h"
typedef std::vector<pat::PackedCandidate> PackedCandidatesCollection;
typedef std::vector<const pat::PackedCandidate *>::const_iterator IT;
#include "DataFormats/PatCandidates/interface/Muon.h"


class IsolationComputer{

    public:
    IsolationComputer(
        edm::Handle<PackedCandidatesCollection>& inputPFcandiadtes, 
        const double isoRadius,
        const double isoRadiusForHLT,
	const double MaxDZForHLT,
        const double dZpv,
        const double dBetaCone,
        const double dBetaValue = 0.2,
        const double pT_treshold = 0.5
        );
    ~IsolationComputer(){}

    // isolation functions
    double pTcharged_iso(const reco::Candidate& tau_cand) const;
    double pTcharged_PU(const reco::Candidate& tau_cand) const;
    double pTphoton(const reco::Candidate& tau_cand) const;
    double pTchargedforhlt_iso(const reco::Candidate& tau_cand, float tau_vz) const;

    // veto muons in the candidate
    void addMuonsToVeto(const std::vector<edm::Ptr<pat::Muon>> inMuToVeto);

    private:

    // PF candidates
    edm::Handle<PackedCandidatesCollection> PFcandCollection_ ;
    std::vector<const pat::PackedCandidate *> charged_, neutral_, pileup_, chargedforhlt_;

    // isolation parameters
    double isoRadius_;
    double isoRadiusForHLT_;
    double MaxDZForHLT_;
    double dZpv_;
    double dBetaCone_;
    double dBetaValue_;
    double pT_treshold_;

    // to veto
    std::vector<edm::Ptr<pat::Muon>> muonsToVeto_;
    const double DELTA_R_TOVETO = 0.0001;

};
#endif