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
#include "TrackingTools/IPTools/interface/IPTools.h"
#include "TrackingTools/PatternTools/interface/ClosestApproachInRPhi.h"
#include "DataFormats/MuonReco/interface/MuonSelectors.h"
#include "DataFormats/MuonReco/interface/Muon.h"
#include "TVector3.h"
#include "TMath.h"

#include "DataFormats/MuonReco/interface/MuonChamberMatch.h"
#include "DataFormats/MuonReco/interface/MuonSegmentMatch.h"

typedef std::pair<const reco::MuonChamberMatch*, const reco::MuonSegmentMatch*> MatchPair;

MatchPair getBetterMatch(const MatchPair& match1, const MatchPair& match2) {
  // Prefer DT over CSC simply because it's closer to IP
  // and will have less multiple scattering (at least for
  // RB1 vs ME1/3 case). RB1 & ME1/2 overlap is tiny
  if (match2.first->detector() == MuonSubdetId::DT and
      match1.first->detector() != MuonSubdetId::DT)
    return match2;

  // For the rest compare local x match. We expect that
  // segments belong to the muon, so the difference in
  // local x is a reflection on how well we can measure it
  if ( abs(match1.first->x - match1.second->x) >
       abs(match2.first->x - match2.second->x) )
    return match2;
    
  return match1;
}


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
                        
                        cand.addUserFloat("mu1_pt",  m1.pt());
                        cand.addUserFloat("mu1_eta", m1.eta());
                        cand.addUserFloat("mu1_phi", m1.phi());
                        cand.addUserFloat("mu1_charge", m1.charge());

                        cand.addUserFloat("mu2_pt",  m2.pt());
                        cand.addUserFloat("mu2_eta", m2.eta());
                        cand.addUserFloat("mu2_phi", m2.phi());
                        cand.addUserFloat("mu2_charge", m2.charge());

                        cand.addUserFloat("mu3_pt",  m3.pt());
                        cand.addUserFloat("mu3_eta", m3.eta());
                        cand.addUserFloat("mu3_phi", m3.phi());
                        cand.addUserFloat("mu3_charge", m3.charge());

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
                        cand.addUserFloat("dr12", -99.); cand.addUserFloat("dr23", -99.); cand.addUserFloat("dr13", -99.);
                        cand.addUserFloat("dr_max", -99.);
                        cand.addUserFloat("dz12", -99.); cand.addUserFloat("dz23", -99.); cand.addUserFloat("dz13", -99.);
                        cand.addUserFloat("dz_max", -99.);
                        cand.addUserFloat("d0", -99.);
                        cand.addUserFloat("d0_sig", -99.);
                        cand.addUserFloat("d0max_sig", -99.);
                        cand.addUserFloat("relative_iso", -99.);
                        cand.addUserFloat("mindca_iso", -99.);

                        cand.addUserInt("mu1_innerTrk_hp", -99);
                        cand.addUserInt("mu2_innerTrk_hp", -99);
                        cand.addUserInt("mu3_innerTrk_hp", -99);

            
                        for (int m = 1; m <= 3; ++m) {
                            for (int s = 1; s <= 2; ++s) {
                                std::string prefix = "mu" + std::to_string(m) + "_match" + std::to_string(s);
                                cand.addUserFloat(prefix + "_dX", -999.f);
                                cand.addUserFloat(prefix + "_pullX", -999.f);
                                cand.addUserFloat(prefix + "_dY", -999.f);
                                cand.addUserFloat(prefix + "_pullY", -999.f);
                                cand.addUserFloat(prefix + "_pullDxDz", -999.f);
                                cand.addUserFloat(prefix + "_pullDyDz", -999.f);
                            }
                        }

                        cand.addUserFloat("pointingAngle", -99);
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

                    // 2. Crea il vettore spostamento (flight direction)
                    // Sottraiamo le posizioni dei vertici (Primary -> Secondary)
                    GlobalVector flightDir(
                        sv.position().x() - cleanPV.position().x(),
                        sv.position().y() - cleanPV.position().y(),
                        sv.position().z() - cleanPV.position().z()
                    );

                    // 3. Ottieni il vettore impulso del tripletto
                    GlobalVector momentum(cand.px(), cand.py(), cand.pz());

                    // 4. Calcolo del coseno dell'angolo di puntamento
                    // Usiamo il prodotto scalare tra i vettori normalizzati (unit vectors)
                    double cosPointingAngle = 0;
                    if (flightDir.mag2() > 0 && momentum.mag2() > 0) {
                        cosPointingAngle = flightDir.unit().dot(momentum.unit());
                    }

                    // Clipping di sicurezza per std::acos
                    cosPointingAngle = std::max(-1.0, std::min(1.0, cosPointingAngle));
                    double pointingAngle = std::acos(cosPointingAngle);

                    // 1. Calcolo dR e dZ tra le coppie di muoni
                    float dr12 = reco::deltaR(m1, m2);
                    float dr23 = reco::deltaR(m2, m3);
                    float dr13 = reco::deltaR(m1, m3);
                    float dr_max = std::max({dr12, dr23, dr13});

                    float dz12 = std::abs(m1.vz() - m2.vz());
                    float dz23 = std::abs(m2.vz() - m3.vz());
                    float dz13 = std::abs(m1.vz() - m3.vz());
                    float dz_max = std::max({dz12, dz23, dz13});

                    // 2. Calcolo d0 e d0_sig (min/max)
                    float dxy1 = std::abs(m1.innerTrack()->dxy(cleanPV.position()));
                    float dxy2 = std::abs(m2.innerTrack()->dxy(cleanPV.position()));
                    float dxy3 = std::abs(m3.innerTrack()->dxy(cleanPV.position()));

                    float dxy1_sig = dxy1 / m1.innerTrack()->dxyError();
                    float dxy2_sig = dxy2 / m2.innerTrack()->dxyError();
                    float dxy3_sig = dxy3 / m3.innerTrack()->dxyError();

                    float d0 = std::min({dxy1, dxy2, dxy3});
                    float d0_sig = std::min({dxy1_sig, dxy2_sig, dxy3_sig});
                    float d0max_sig = std::max({dxy1_sig, dxy2_sig, dxy3_sig});

                    // Esempio per il muone m1 (ripeti la logica o usa un loop se preferisci)
                    bool m1_hp = (m1.innerTrack().isNonnull()) ? m1.innerTrack()->quality(reco::TrackBase::highPurity) : false;
                    bool m2_hp = (m2.innerTrack().isNonnull()) ? m2.innerTrack()->quality(reco::TrackBase::highPurity) : false;
                    bool m3_hp = (m3.innerTrack().isNonnull()) ? m3.innerTrack()->quality(reco::TrackBase::highPurity) : false;


                    // 3. Calcolo Isolamento (Esempio semplificato mindca_iso e relative_iso)
                    // Nota: relative_iso solitamente è (somma pT tracce dR<0.3) / pT_tripletto
                    float sum_pt_iso = 0;
                    float min_dca = 999.;
                    for (const auto& track : *candidates) {
                        if (track.charge() == 0 || track.pt() < 0.5 || !track.hasTrackDetails()) continue;
                        
                        // Distanza angolare dal tripletto
                        float dr = reco::deltaR(track, p4_ref);
                        
                        // Escludi i tre muoni sorgente (usando gli indici o un dr molto piccolo)
                        if (reco::deltaR(track, m1) < 0.005 || reco::deltaR(track, m2) < 0.005 || reco::deltaR(track, m3) < 0.005) continue;

                        // 1. Relative Isolation (somma pT entro dR < 0.3)
                        if (dr < 0.3) {
                            sum_pt_iso += track.pt();
                        }

                        // 2. Calcolo DCA (Distance of Closest Approach)
                        reco::TransientTrack ttIso = ttb.build(track.pseudoTrack());
                        if (ttIso.isValid()) {
                            // Calcola il punto di minimo approccio rispetto alla posizione del vertice SV
                            TrajectoryStateClosestToPoint pca = ttIso.trajectoryStateClosestToPoint(sv.position());
                            if (pca.isValid()) {
                                float dca_val = (pca.position() - sv.position()).mag();
                                if (dca_val < min_dca) min_dca = dca_val;
                            }
                        }
                    }
                    float relative_iso = sum_pt_iso / p4_ref.pt();
                    cand.setP4(p4_ref); 
                    cand.setCharge(m1.charge() + m2.charge() + m3.charge());
                    cand.setVertex(reco::Candidate::Point(sv.position().x(), sv.position().y(), sv.position().z()));

                    // Basic Info & Indices
                    cand.addUserInt("mu1_idx", i); cand.addUserInt("mu2_idx", j); cand.addUserInt("mu3_idx", k);
                    
                    cand.addUserFloat("mu1_pt",  m1.pt());
                    cand.addUserFloat("mu1_eta", m1.eta());
                    cand.addUserFloat("mu1_phi", m1.phi());

                    cand.addUserFloat("mu2_pt",  m2.pt());
                    cand.addUserFloat("mu2_eta", m2.eta());
                    cand.addUserFloat("mu2_phi", m2.phi());

                    cand.addUserFloat("mu3_pt",  m3.pt());
                    cand.addUserFloat("mu3_eta", m3.eta());
                    cand.addUserFloat("mu3_phi", m3.phi());
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
                    
                    cand.addUserFloat("innerTrk_highPurity_1", m1_hp);
                    cand.addUserFloat("innerTrk_highPurity_2", m2_hp);
                    cand.addUserFloat("innerTrk_highPurity_3", m3_hp); // mu3 treated as 'track'
                    

                    cand.addUserFloat("cos_3d", maxCos);
                    
                    cand.addUserFloat("dr12", dr12); cand.addUserFloat("dr23", dr23); cand.addUserFloat("dr13", dr13);
                    cand.addUserFloat("dr_max", dr_max);
                    cand.addUserFloat("dz12", dz12); cand.addUserFloat("dz23", dz23); cand.addUserFloat("dz13", dz13);
                    cand.addUserFloat("dz_max", dz_max);
                    cand.addUserFloat("d0", d0);
                    cand.addUserFloat("d0_sig", d0_sig);
                    cand.addUserFloat("d0max_sig", d0max_sig);
                    cand.addUserFloat("relative_iso", relative_iso);
                    cand.addUserFloat("mindca_iso", min_dca);

                    cand.addUserInt("mu1_innerTrk_hp", m1_hp);
                    cand.addUserInt("mu2_innerTrk_hp", m2_hp);
                    cand.addUserInt("mu3_innerTrk_hp", m3_hp);

                    fillMatchInfo(m1, cand, "mu1");
                    fillMatchInfo(m2, cand, "mu2");
                    fillMatchInfo(m3, cand, "mu3");

                    cand.addUserFloat("pointingAngle", pointingAngle);
                    ret_val->push_back(cand);
                }
            }
        }
        evt.put(std::move(ret_val));
    }

    void fillMatchInfo(const pat::Muon& muon, pat::CompositeCandidate& cand, std::string prefix) const {
    const int n_stations = 2;
    std::vector<MatchPair> matches(n_stations, {nullptr, nullptr});

    for (const auto& chamberMatch : muon.matches()) {
        int station = chamberMatch.station() - 1;
        if (station < 0 || station >= n_stations) continue;

        for (const auto& segmentMatch : chamberMatch.segmentMatches) {
            if (!(segmentMatch.isMask(reco::MuonSegmentMatch::BestInStationByDR) &&
                  segmentMatch.isMask(reco::MuonSegmentMatch::BelongsToTrackByDR)))
                continue;

            MatchPair current_match(&chamberMatch, &segmentMatch);
            if (matches[station].first) matches[station] = getBetterMatch(matches[station], current_match);
            else matches[station] = current_match;
        }
    }

    for (int s = 0; s < n_stations; ++s) {
        std::string label = prefix + "_match" + std::to_string(s + 1);
        if (matches[s].first && matches[s].second) {
            float dX = matches[s].first->x - matches[s].second->x;
            float errX = std::sqrt(std::pow(matches[s].first->xErr, 2) + std::pow(matches[s].second->xErr, 2));
            cand.addUserFloat(label + "_dX", dX);
            cand.addUserFloat(label + "_pullX", (errX > 0) ? dX / errX : -999.f);
            // --- Coordinate Y ---
            float dY = matches[s].first->y - matches[s].second->y;
            float errY = std::sqrt(std::pow(matches[s].first->yErr, 2) + std::pow(matches[s].second->yErr, 2));
            cand.addUserFloat(label + "_dY", dY);
            cand.addUserFloat(label + "_pullY", (errY > 0) ? dY / errY : -999.f);

            // --- Pendenze (Direction matching) ---
            float dDxDz = matches[s].first->dXdZ - matches[s].second->dXdZ;
            float errDxDz = std::sqrt(std::pow(matches[s].first->dXdZErr, 2) + std::pow(matches[s].second->dXdZErr, 2));
            cand.addUserFloat(label + "_pullDxDz", (errDxDz > 0) ? dDxDz / errDxDz : -999.f);

            float dDyDz = matches[s].first->dYdZ - matches[s].second->dYdZ;
            float errDyDz = std::sqrt(std::pow(matches[s].first->dYdZErr, 2) + std::pow(matches[s].second->dYdZErr, 2));
            cand.addUserFloat(label + "_pullDyDz", (errDyDz > 0) ? dDyDz / errDyDz : -999.f);
        } else {
            cand.addUserFloat(label + "_dX", -999.f);
            cand.addUserFloat(label + "_pullX", -999.f);
            cand.addUserFloat(label + "_dY", -999.f);
            cand.addUserFloat(label + "_pullY", -999.f);
            cand.addUserFloat(label + "_pullDxDz", -999.f);
            cand.addUserFloat(label + "_pullDyDz", -999.f);
        }
    }
}

private:
    const edm::EDGetTokenT<pat::MuonCollection> muonsToken_;
    const edm::EDGetTokenT<reco::VertexCollection> vtxToken_;
    const edm::EDGetTokenT<pat::PackedCandidateCollection> pcToken_;
    const edm::EDGetTokenT<reco::BeamSpot> bsToken_;
    const edm::ESGetToken<TransientTrackBuilder, TransientTrackRecord> ttbToken_;
};

DEFINE_FWK_MODULE(Tau3MuBuilder);