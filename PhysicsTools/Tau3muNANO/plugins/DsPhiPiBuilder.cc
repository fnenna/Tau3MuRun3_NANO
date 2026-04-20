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
#include "DataFormats/Math/interface/deltaR.h"
#include "TVector3.h"

class Tau2Mu1TrkBuilder : public edm::global::EDProducer<> {
public:
    explicit Tau2Mu1TrkBuilder(const edm::ParameterSet& cfg) :
        muonsToken_(consumes<pat::MuonCollection>(cfg.getParameter<edm::InputTag>("muons"))),
        tracksToken_(consumes<pat::PackedCandidateCollection>(cfg.getParameter<edm::InputTag>("tracks"))),
        vtxToken_(consumes<reco::VertexCollection>(cfg.getParameter<edm::InputTag>("vertices"))),
        pcToken_(consumes<pat::PackedCandidateCollection>(cfg.getParameter<edm::InputTag>("candidates"))),
        bsToken_(consumes<reco::BeamSpot>(cfg.getParameter<edm::InputTag>("beamSpot"))),
        ttbToken_(esConsumes<TransientTrackBuilder, TransientTrackRecord>(edm::ESInputTag("", "TransientTrackBuilder"))) {
        produces<pat::CompositeCandidateCollection>();
    }

    void produce(edm::StreamID, edm::Event& evt, const edm::EventSetup& iSetup) const override {
        edm::Handle<pat::MuonCollection> muons;
        evt.getByToken(muonsToken_, muons);
        edm::Handle<pat::PackedCandidateCollection> tracks;
        evt.getByToken(tracksToken_, tracks);
        edm::Handle<reco::VertexCollection> vertices;
        evt.getByToken(vtxToken_, vertices);
        edm::Handle<pat::PackedCandidateCollection> candidates;
        evt.getByToken(pcToken_, candidates);
        edm::Handle<reco::BeamSpot> beamSpot;
        evt.getByToken(bsToken_, beamSpot);

        const auto& ttb = iSetup.getData(ttbToken_);
        auto ret_val = std::make_unique<pat::CompositeCandidateCollection>();
        PVRefitter pvRefitter;

        // --- Contatori per il Breakdown ---
        int n_initial_comb = 0;
        int n_fail_tt3 = 0;
        int n_fail_dR = 0;
        int n_fail_eta_collinear = 0;
        int n_fail_dimuon_mass = 0;
        int n_fail_triplet_mass = 0;
        int n_fail_charge = 0;
        int n_fail_track_details = 0;
        int n_fail_sv_fit = 0;
        int n_fail_sv_ndof = 0;
        int n_fail_no_valid_pv = 0;
        int n_saved = 0;

        for (size_t i = 0; i < muons->size(); ++i) {
            for (size_t j = i + 1; j < muons->size(); ++j) {
                for (size_t k = 0; k < tracks->size(); ++k) {
                    n_initial_comb++;
                    
                    const pat::Muon &m1 = muons->at(i), &m2 = muons->at(j);
                    const pat::PackedCandidate &tr = tracks->at(k);

                    // 1. Transient Track check
                    auto tt3 = ttb.build(tr.pseudoTrack());
                    if (!tt3.isValid()) { n_fail_tt3++; continue; }

                    // 2. Overlap dR
                    double dR_13 = reco::deltaR(m1, tr);
                    double dR_23 = reco::deltaR(m2, tr);
                    double dR_12 = reco::deltaR(m1, m2);
                    if(dR_13 < 0.01 || dR_23 < 0.01 || dR_12 < 0.01) { n_fail_dR++; continue; }

                    // 3. Eta Collinearity (il taglio infinitesimale che avevamo discusso)
                    if (std::abs(m1.eta() - tr.eta()) < 1e-6 || 
                        std::abs(m2.eta() - tr.eta()) < 1e-6 || 
                        std::abs(m1.eta() - m2.eta()) < 1e-6) {
                        n_fail_eta_collinear++;
                        continue;
                    }

                    // 4. DiMuon Mass Cut (Replica del pre-filtro Python)
                    auto dimu_p4 = m1.p4() + m2.p4();

                    // 5. Triplet Raw Mass
                    auto p4_raw = dimu_p4 + tr.p4();
                    if (p4_raw.mass() <= 0.8 || p4_raw.mass() >= 3.0) { n_fail_triplet_mass++; continue; }

                    // 6. Charge & Track details
                    if (std::abs(m1.charge() + m2.charge()) != 0) { n_fail_charge++; continue; }
                    if (std::abs(m1.charge() + m2.charge() + tr.charge()) != 1) { n_fail_charge++; continue; }
                    if (m1.innerTrack().isNull() || m2.innerTrack().isNull() || !tr.hasTrackDetails()) { n_fail_track_details++; continue; }

                    // 7. SV Fit
                    std::vector<reco::TransientTrack> tt = {
                        ttb.build(m1.innerTrack()), 
                        ttb.build(m2.innerTrack()), 
                        ttb.build(tr.pseudoTrack())
                    };
                    KalmanVertexFitter svFitter(true);
                    TransientVertex sv = svFitter.vertex(tt);

                    //if (!sv.isValid() || !sv.hasRefittedTracks() || sv.totalChiSquared() <= 0) { n_fail_sv_fit++; continue; }
                    if (!sv.isValid()) { n_fail_sv_fit++; continue; }
                    if (sv.refittedTracks().size() <= 2) { n_fail_sv_ndof++; continue; }

                    // --- Calcolo cinematica refittata ---
                    reco::Candidate::LorentzVector p4_ref(0,0,0,0);
                    int idx_rt = 0;
                    for(const auto& rt : sv.refittedTracks()) {
                        double mass_sq = (idx_rt < 2) ? 0.0111636 : 0.019479; 
                        p4_ref += reco::Candidate::LorentzVector(rt.track().px(), rt.track().py(), rt.track().pz(), std::sqrt(rt.track().p2() + mass_sq));
                        idx_rt++;
                    }

                    // 8. PV Selection & Refit
                    std::vector<int> validVtxIndices;
                    for (const auto& pfc : *candidates) {
                        if (pfc.charge() == 0 || pfc.vertexRef().isNull() || !pfc.hasTrackDetails()) continue;
                        int fromPV = pfc.fromPV(pfc.vertexRef().key());
                        if (fromPV < 2) continue;
                        if (fromPV==2 && pfc.pvAssociationQuality()!= pat::PackedCandidate::UsedInFitLoose ) continue;
                        validVtxIndices.push_back(pfc.vertexRef().key());
                    }
                    std::sort(validVtxIndices.begin(), validVtxIndices.end());
                    validVtxIndices.erase(std::unique(validVtxIndices.begin(), validVtxIndices.end()), validVtxIndices.end());

                    if (validVtxIndices.empty() || vertices->empty()) { n_fail_no_valid_pv++; continue; }

                    int b_idx = -1; double maxCos = -1.0;
                    TVector3 svP(sv.position().x(), sv.position().y(), sv.position().z());
                    TVector3 pT(p4_ref.px(), p4_ref.py(), p4_ref.pz());

                    for (size_t v = 0; v < vertices->size(); ++v) {
                        if (std::find(validVtxIndices.begin(), validVtxIndices.end(), (int)v) == validVtxIndices.end()) continue;
                        TVector3 dv(svP.x() - vertices->at(v).x(), svP.y() - vertices->at(v).y(), svP.z() - vertices->at(v).z());
                        double c = dv.Dot(pT) / (dv.Mag() * pT.Mag());
                        if (c > maxCos) { maxCos = c; b_idx = v; }
                    }

                    pat::CompositeCandidate cand;
                    [[maybe_unused]] bool goodPV = false;
                    //reco::Vertex cleanPV;

                    if (b_idx == -1) continue;
                    std::vector<reco::TransientTrack> pvTTracks;
                    for (const auto& pfc : *candidates) {
                        if (pfc.charge() == 0 || !pfc.hasTrackDetails() || pfc.vertexRef().isNull()) continue;
                        if (pfc.vertexRef().key() != (size_t)b_idx) continue;
                        int fromPV = pfc.fromPV(pfc.vertexRef().key());
                        if (fromPV < 2) continue;
                        if (fromPV == 2 && pfc.pvAssociationQuality() != pat::PackedCandidate::UsedInFitLoose) continue;
                        
                        auto pv_tt = ttb.build(pfc.pseudoTrack());
                        if (pv_tt.isValid()) pvTTracks.push_back(pv_tt);
                    }

                    //cleanPV = pvRefitter.refit(tt, vertices->at(b_idx), pvTTracks);
                    auto [cleanPV, pvStatus] = pvRefitter.refit(tt, vertices->at(b_idx), pvTTracks);
                    if (cleanPV.isValid() && pvStatus == 1) goodPV = true;
                    else { n_fail_no_valid_pv++; continue; } // Silent drop del WF1

                    // --- 1. 3D Flight Distance (PVSV) ---
                    VertexDistance3D dist3D;
                    auto d3d = dist3D.distance(sv, cleanPV);

                    double flightDist    = d3d.value();
                    double flightDistErr = d3d.error();
                    double flightDistSig = d3d.significance();

                    // --- 2. Transverse distance (XY) ---
                    VertexDistanceXY Vert_distXY;
                    auto d2d = Vert_distXY.distance(sv, cleanPV);

                    double distXY    = d2d.value();
                    double distXYErr = d2d.error();
                    double distXYSig = d2d.significance();

                    // --- 3. BeamSpot distance (XY) ---
                    reco::Vertex::Point bsPoint(beamSpot->x0(), beamSpot->y0(), beamSpot->z0());
                    reco::Vertex::Error bsError = beamSpot->covariance3D();
                    reco::Vertex bsVertex(bsPoint, bsError);

                    auto dBS = Vert_distXY.distance(sv, bsVertex);

                    double flightDistBS    = dBS.value();
                    double flightDistBSErr = dBS.error();
                    double flightDistBSSig = dBS.significance();
                    // --- Fill the Candidate ---
                    cand.setP4(p4_ref);
                    cand.setCharge(m1.charge() + m2.charge() + tr.charge());

                    // Kinematics & Basic
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

                    // Flight Distance
                    cand.addUserFloat("flightDist", flightDist);
                    cand.addUserFloat("flightDistErr", flightDistErr);
                    cand.addUserFloat("flightDistSig", flightDist / flightDistErr);
                    cand.addUserFloat("distXY", distXY);
                    cand.addUserFloat("distXYSig", distXY / distXYErr);
                    cand.addUserFloat("flightDistBS", flightDistBS);

                    // Refitted Tracks
                    cand.addUserFloat("refit_mu1_pt", sv.refittedTracks()[0].track().pt());
                    cand.addUserFloat("refit_mu2_pt", sv.refittedTracks()[1].track().pt());
                    cand.addUserFloat("refit_tr_pt",  sv.refittedTracks()[2].track().pt());

                    // Impact Parameters (DXY)
                    cand.addUserFloat("dxy_mu1", m1.innerTrack()->dxy(cleanPV.position()));
                    cand.addUserFloat("dxy_mu2", m2.innerTrack()->dxy(cleanPV.position()));
                    cand.addUserFloat("dxy_tr",  tr.pseudoTrack().dxy(cleanPV.position()));

                    ret_val->push_back(cand);
                    n_saved++;
                }
            }
        }

        // --- BREAKDOWN LOG PRINTING ---
        std::cout << "\n==== EVENT BREAKDOWN (ID: " << evt.id().event() << ") ====" << std::endl;
        std::cout << "1. Combinazioni Iniziali:   " << n_initial_comb << std::endl;
        std::cout << "2. Fallite Traccia Builder: " << n_fail_tt3 << std::endl;
        std::cout << "3. Fallite Overlap dR:      " << n_fail_dR << std::endl;
        std::cout << "4. Fallite Eta Collineari:  " << n_fail_eta_collinear << std::endl;
        std::cout << "5. Fallite Massa DiMuon:    " << n_fail_dimuon_mass << std::endl;
        std::cout << "6. Fallite Massa Tripletto: " << n_fail_triplet_mass << std::endl;
        std::cout << "7. Fallite Carica/Dettagli: " << n_fail_charge + n_fail_track_details << std::endl;
        std::cout << "8. Fallite SV Fit/NDOF:     " << n_fail_sv_fit + n_fail_sv_ndof << std::endl;
        std::cout << "9. Fallite PV (SilentDrop): " << n_fail_no_valid_pv << std::endl;
        std::cout << "TOTAL SAVED:                " << n_saved << std::endl;
        std::cout << "==========================================\n" << std::endl;

        evt.put(std::move(ret_val));
    }

private:
    const edm::EDGetTokenT<pat::MuonCollection> muonsToken_;
    const edm::EDGetTokenT<pat::PackedCandidateCollection> tracksToken_;
    const edm::EDGetTokenT<reco::VertexCollection> vtxToken_;
    const edm::EDGetTokenT<pat::PackedCandidateCollection> pcToken_;
    const edm::EDGetTokenT<reco::BeamSpot> bsToken_;
    const edm::ESGetToken<TransientTrackBuilder, TransientTrackRecord> ttbToken_;
};

DEFINE_FWK_MODULE(Tau2Mu1TrkBuilder);