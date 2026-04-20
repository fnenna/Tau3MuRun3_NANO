#include "FWCore/Framework/interface/global/EDProducer.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "DataFormats/PatCandidates/interface/Muon.h"
#include "DataFormats/PatCandidates/interface/CompositeCandidate.h"
#include "DataFormats/PatCandidates/interface/PackedCandidate.h"
#include "DataFormats/BeamSpot/interface/BeamSpot.h"
#include "TrackingTools/TransientTrack/interface/TransientTrackBuilder.h"
#include "TrackingTools/Records/interface/TransientTrackRecord.h"
#include "RecoVertex/KalmanVertexFit/interface/KalmanVertexFitter.h"
#include "PhysicsTools/Tau3muNANO/interface/PVRefitter.h"
#include "RecoVertex/VertexTools/interface/VertexDistance3D.h"
#include "RecoVertex/VertexTools/interface/VertexDistanceXY.h"
#include "TVector3.h"
#include "TMath.h"

class Tau3MuBuilder : public edm::global::EDProducer<> {
public:
    explicit Tau3MuBuilder(const edm::ParameterSet& cfg) :
        muonsToken_(consumes<pat::MuonCollection>(cfg.getParameter<edm::InputTag>("src"))),
        vtxToken_(consumes<reco::VertexCollection>(cfg.getParameter<edm::InputTag>("vertices"))),
        pcToken_(consumes<pat::PackedCandidateCollection>(cfg.getParameter<edm::InputTag>("candidates"))),
        bsToken_(consumes<reco::BeamSpot>(cfg.getParameter<edm::InputTag>("beamSpot"))),
        ttbToken_(esConsumes<TransientTrackBuilder, TransientTrackRecord>(edm::ESInputTag("", "TransientTrackBuilder"))) {
        produces<pat::CompositeCandidateCollection>();
    }

    void produce(edm::StreamID, edm::Event& evt, const edm::EventSetup& iSetup) const override {
        edm::Handle<pat::MuonCollection> muons;
        evt.getByToken(muonsToken_, muons);
        edm::Handle<reco::VertexCollection> vertices;
        evt.getByToken(vtxToken_, vertices);
        edm::Handle<pat::PackedCandidateCollection> candidates;
        evt.getByToken(pcToken_, candidates);
        edm::Handle<reco::BeamSpot> beamSpot;
        evt.getByToken(bsToken_, beamSpot);

        const auto& ttb = iSetup.getData(ttbToken_);
        auto ret_val = std::make_unique<pat::CompositeCandidateCollection>();
        PVRefitter pvRefitter;

        for (size_t i = 0; i < muons->size(); ++i) {
            for (size_t j = i + 1; j < muons->size(); ++j) {
                for (size_t k = j + 1; k < muons->size(); ++k) {
                    // --- Build Candidate ---
                    pat::CompositeCandidate cand;
                    const pat::Muon &m1 = muons->at(i), &m2 = muons->at(j), &m3 = muons->at(k);
                    if (m1.innerTrack().isNull() || m2.innerTrack().isNull() || m3.innerTrack().isNull()) continue;
                    if (std::abs(m1.charge() + m2.charge() + m3.charge()) != 1) continue;

                    std::vector<reco::TransientTrack> muTTracks = {ttb.build(m1.innerTrack()), ttb.build(m2.innerTrack()), ttb.build(m3.innerTrack())};
                    KalmanVertexFitter svFitter(true);
                    TransientVertex sv = svFitter.vertex(muTTracks);
                    if (!sv.isValid() || !sv.hasRefittedTracks()){
                        cand.setP4(reco::Candidate::LorentzVector(-99., -99., -99., -99.)); 
                        cand.setCharge(m1.charge() + m2.charge() + m3.charge());
                        cand.setVertex(reco::Candidate::Point(-99., -99., -99.));

                        cand.addUserInt("mu1_idx", i); cand.addUserInt("mu2_idx", j); cand.addUserInt("mu3_idx", k);
                        
                        // SV Quality & Mass
                        cand.addUserFloat("sv_mass", -99.);
                        cand.addUserFloat("sv_prob", -99.);
                        cand.addUserFloat("sv_chi2", -99.);
                        cand.addUserFloat("sv_ndof", -99.);


                        // Positions
                        cand.addUserFloat("sv_x", -99.);
                        cand.addUserFloat("sv_y", -99.);
                        cand.addUserFloat("sv_z", -99.);
                        cand.addUserFloat("pv_x", -99.);
                        cand.addUserFloat("pv_y", -99.);
                        cand.addUserFloat("pv_z", -99.);
                        cand.addUserFloat("pv_orig_x", -99.); 
                        cand.addUserFloat("pv_orig_y", -99.); 
                        cand.addUserFloat("pv_orig_z", -99.);

                        // SV Refitted Kinematics (Matching twomu1trk names)
                        cand.addUserFloat("refit_mu1_pt", -99.);
                        cand.addUserFloat("refit_mu2_pt", -99.);
                        cand.addUserFloat("refit_mu3_pt",  -99.); // Name kept for consistency


                        // Displacement & Significance
                        cand.addUserFloat("flightDist", -99.);
                        cand.addUserFloat("flightDistErr", -99.);
                        cand.addUserFloat("flightDistSig", -99.);
                        cand.addUserFloat("lxy_pv", -99.); cand.addUserFloat("lxy_pv_err", -99.);
                        cand.addUserFloat("distXY", -99.);
                        cand.addUserFloat("distXYSig", -99.);
                        cand.addUserFloat("l3d_pv", -99.); cand.addUserFloat("l3d_pv_err", -99.);
                        cand.addUserFloat("flightDistBS", -99.);
                        cand.addUserFloat("lxy_bs", -99.); cand.addUserFloat("lxy_bs_err", -99.);
                        
                        // Impact Parameters
                        cand.addUserFloat("dxy_mu1", -99.);
                        cand.addUserFloat("dxy_mu2", -99.);
                        cand.addUserFloat("dxy_mu3", -99.); // mu3 treated as 'track'
                        
                        cand.addUserFloat("cos_3d", -99.);
                        ret_val->push_back(cand);
                        continue;
                    }
                    // --- Refitted Kinematics ---
                    reco::Candidate::LorentzVector p4_ref(0,0,0,0);
                    std::vector<double> refit_pts;
                    for(const auto& rt : sv.refittedTracks()) {
                        double e = std::sqrt(rt.track().p2() + 0.0111636);
                        p4_ref += reco::Candidate::LorentzVector(rt.track().px(), rt.track().py(), rt.track().pz(), e);
                        refit_pts.push_back(rt.track().pt());
                    }

                    // --- PV Selection & Refit Logic ---
                    std::vector<int> validVtxIndices;
                    for (const auto& pfc : *candidates) {
                        if (pfc.charge() == 0 || pfc.vertexRef().isNull() || !pfc.hasTrackDetails()) continue;
                        int fromPV = pfc.fromPV(pfc.vertexRef().key());
                        if (fromPV < 2) continue;
                        if (fromPV == 2 && pfc.pvAssociationQuality() != pat::PackedCandidate::UsedInFitLoose) continue;
                        validVtxIndices.push_back(pfc.vertexRef().key());
                    }
                    std::sort(validVtxIndices.begin(), validVtxIndices.end());
                    validVtxIndices.erase(std::unique(validVtxIndices.begin(), validVtxIndices.end()), validVtxIndices.end());

                    uint b_idx = -1; 
                    double maxCos = -1.0;
                    TVector3 svP(sv.position().x(), sv.position().y(), sv.position().z());
                    TVector3 pT(p4_ref.px(), p4_ref.py(), p4_ref.pz());

                    for (size_t v = 0; v < vertices->size(); ++v) {
                        if (std::find(validVtxIndices.begin(), validVtxIndices.end(), (int)v) == validVtxIndices.end()) continue;
                        TVector3 dv(svP.x() - vertices->at(v).x(),
                        svP.y() - vertices->at(v).y(),
                        svP.z() - vertices->at(v).z());
                        double c = dv.Dot(pT) / (dv.Mag() * pT.Mag());
                        if (c > maxCos) {
                            maxCos = c;
                            b_idx = v;
                        }
                    }

                    if (b_idx == (uint)-1) continue; 
                    const reco::Vertex& bestPV = vertices->at(b_idx);

                    std::vector<reco::TransientTrack> pvTTracks;
                    for (const auto& c : *candidates) {
                        if (c.charge() == 0 || !c.hasTrackDetails() || c.vertexRef().isNull()) continue;
                        if (c.vertexRef().key() != b_idx) continue;

                        int quality = c.pvAssociationQuality();
                        int fromPV = c.fromPV(c.vertexRef().key());

                        if (fromPV < 2) continue;
                        if (fromPV == 2 && quality != pat::PackedCandidate::UsedInFitLoose) continue;
                        pvTTracks.push_back(ttb.build(c.pseudoTrack()));
                    }

                    //reco::Vertex cleanPV = pvRefitter.refit(muTTracks, bestPV, pvTTracks);
                    auto [cleanPV, pvStatus] = pvRefitter.refit(muTTracks, bestPV, pvTTracks);
                    if (!cleanPV.isValid()) continue;

                    // --- Displacement Calculations ---
                    VertexDistanceXY distXY; 
                    VertexDistance3D dist3D;
                    auto d2d = distXY.distance(sv, cleanPV);
                    auto d3d = dist3D.distance(sv, cleanPV);
                    
                    reco::Vertex::Point bsPoint(beamSpot->x0(), beamSpot->y0(), beamSpot->z0());
                    reco::Vertex::Error bsError = beamSpot->covariance3D();
                    reco::Vertex bsVertex(bsPoint, bsError);
                    auto dBS = distXY.distance(sv, bsVertex);

                    cand.setP4(p4_ref); 
                    cand.setCharge(m1.charge() + m2.charge() + m3.charge());
                    cand.setVertex(reco::Candidate::Point(sv.position().x(), sv.position().y(), sv.position().z()));

                    // Basic Info & Indices
                    cand.addUserInt("mu1_idx", i); cand.addUserInt("mu2_idx", j); cand.addUserInt("mu3_idx", k);
                    
                    // SV Quality & Mass
                    cand.addUserFloat("sv_mass", p4_ref.M());
                    cand.addUserFloat("sv_prob", TMath::Prob(sv.totalChiSquared(), sv.degreesOfFreedom()));
                    cand.addUserFloat("sv_chi2", sv.totalChiSquared());
                    cand.addUserFloat("sv_ndof", sv.degreesOfFreedom());


                    // Positions
                    cand.addUserFloat("sv_x", sv.position().x());
                    cand.addUserFloat("sv_y", sv.position().y());
                    cand.addUserFloat("sv_z", sv.position().z());
                    cand.addUserFloat("pv_x", cleanPV.x());
                    cand.addUserFloat("pv_y", cleanPV.y());
                    cand.addUserFloat("pv_z", cleanPV.z());
                    cand.addUserFloat("pv_orig_x", bestPV.x()); 
                    cand.addUserFloat("pv_orig_y", bestPV.y()); 
                    cand.addUserFloat("pv_orig_z", bestPV.z());

                    // SV Refitted Kinematics (Matching twomu1trk names)
                    cand.addUserFloat("refit_mu1_pt", refit_pts[0]);
                    cand.addUserFloat("refit_mu2_pt", refit_pts[1]);
                    cand.addUserFloat("refit_mu3_pt",  refit_pts[2]); // Name kept for consistency


                    // Displacement & Significance
                    cand.addUserFloat("flightDist", d3d.value());
                    cand.addUserFloat("flightDistErr", d3d.error());
                    cand.addUserFloat("flightDistSig", d3d.value() / d3d.error());
                    cand.addUserFloat("lxy_pv", d2d.value()); cand.addUserFloat("lxy_pv_err", d2d.error());
                    cand.addUserFloat("distXY", d2d.value());
                    cand.addUserFloat("distXYSig", d2d.value() / d2d.error());
                    cand.addUserFloat("l3d_pv", d3d.value()); cand.addUserFloat("l3d_pv_err", d3d.error());
                    cand.addUserFloat("flightDistBS", dBS.value());
                    cand.addUserFloat("lxy_bs", dBS.value()); cand.addUserFloat("lxy_bs_err", dBS.error());
                    
                    // Impact Parameters
                    cand.addUserFloat("dxy_mu1", m1.innerTrack()->dxy(cleanPV.position()));
                    cand.addUserFloat("dxy_mu2", m2.innerTrack()->dxy(cleanPV.position()));
                    cand.addUserFloat("dxy_mu3",  m3.innerTrack()->dxy(cleanPV.position())); // mu3 treated as 'track'
                    
                    cand.addUserFloat("cos_3d", maxCos);
                    
                    ret_val->push_back(cand);
                }
            }
        }
        evt.put(std::move(ret_val));
    }

private:
    const edm::EDGetTokenT<pat::MuonCollection> muonsToken_;
    const edm::EDGetTokenT<reco::VertexCollection> vtxToken_;
    const edm::EDGetTokenT<pat::PackedCandidateCollection> pcToken_;
    const edm::EDGetTokenT<reco::BeamSpot> bsToken_;
    const edm::ESGetToken<TransientTrackBuilder, TransientTrackRecord> ttbToken_;
};

DEFINE_FWK_MODULE(Tau3MuBuilder);