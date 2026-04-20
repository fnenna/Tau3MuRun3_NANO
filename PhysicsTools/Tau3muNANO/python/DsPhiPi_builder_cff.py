import FWCore.ParameterSet.Config as cms
from PhysicsTools.NanoAOD.common_cff import *
from PhysicsTools.NanoAOD.simpleGenParticleFlatTableProducer_cfi import simpleGenParticleFlatTableProducer
from PhysicsTools.NanoAOD.muons_cff import muonTable
# --- 0. CONTROL PARAMETERS ---
isMC = False 
HLT_path_list = cms.vstring(
        "HLT_DoubleMu3_Trk_Tau3mu", 
        "HLT_DoubleMu3_TkMu_DsTau3Mu_v", 
        "HLT_DoubleMu3_Trk_Tau3mu_NoL1Mass_v", 
        "HLT_DoubleMu4_3_LowMass_v", 
        "HLT_DoubleMu4_LowMass_Displaced_v"
    )
# --- 1. EVENT FILTERS (HLT & SKIMMING) ---

# HLT Filter: Select events passing specific trigger paths
hltFilter = cms.EDFilter("HLTHighLevel",
    HLTPaths = cms.vstring([path + "*" for path in HLT_path_list]),
    throw = cms.bool(False)
)

# Base Muon Selection: Kinetic cuts and quality requirements
selectedMuons = cms.EDFilter("PATMuonSelector",
    src = cms.InputTag("slimmedMuons"),
    cut = cms.string("pt > 2.0 && abs(eta) < 2.4 && (innerTrack().isNonnull) && (charge!=0) && (innerTrack().hitPattern().numberOfValidPixelHits()>0)"),
    filter = cms.bool(True)                                
)

# Preliminary Filter: Require at least 2 selected muons
TwoMuonsFilter = cms.EDFilter("CandViewCountFilter",
    src = cms.InputTag("selectedMuons"),
    minNumber = cms.uint32(2)
)

# Track Selection: Select high-quality tracks from PFCandidates
selectedTracks = cms.EDFilter("PATPackedCandidateSelector",
    src = cms.InputTag("packedPFCandidates"),
    cut = cms.string("pt > 2 && abs(eta)<2.4 && (charge!=0) && hasTrackDetails() && trackerLayersWithMeasurement()>5 && pixelLayersWithMeasurement()>=1"),
)

# Preliminary Filter: Require at least 1 selected track
oneTrackFilter = cms.EDFilter("CandViewCountFilter",
    src = cms.InputTag("selectedTracks"),
    minNumber = cms.uint32(1)
)

# Technical Skim: Combiner for Muon pairs (Mass resonance window)
DiMuonCand = cms.EDProducer("CandViewShallowCloneCombiner",
    checkCharge = cms.bool(False),
    cut = cms.string('(abs(charge)==0) && (mass < 1.5) && (mass > 0.5)'),
    decay = cms.string("selectedMuons selectedMuons")
)

DiMuonCandFilter = cms.EDFilter("CandViewCountFilter",
    src = cms.InputTag("DiMuonCand"),
    minNumber = cms.uint32(1)
)

# Final Candidate Combiner: 2 Muons + 1 Track (Global mass window)
TwoMuonsOneTrackCand = cms.EDProducer("CandViewShallowCloneCombiner",
    checkCharge = cms.bool(False),
    cut = cms.string('(abs(charge)==1) && ((daughter(0).charge+daughter(1).charge)==0) && (mass < 3.0) && (mass > 0.8)'),
    decay = cms.string("selectedMuons selectedMuons selectedTracks")
)

# Main Skim Filter: Drop events without at least one valid triplet candidate
tauCountFilter = cms.EDFilter("CandViewCountFilter",
    src = cms.InputTag("TwoMuonsOneTrackCand"),
    minNumber = cms.uint32(1)
)

# --- 2. MONTE CARLO MODULES (Conditional on isMC) ---

if isMC:
    # Gen Particle Pruning: Keep only interesting particles for signal/background study
    myFinalGenParticles = cms.EDProducer("GenParticlePruner",
        src = cms.InputTag("prunedGenParticles"),
        select = cms.vstring(
            "drop *",
            "keep abs(pdgId)==13 | abs(pdgId)==15 | abs(pdgId)==11 | abs(pdgId)==211 | abs(pdgId)==321 | abs(pdgId)==431 | abs(pdgId)==333 | abs(pdgId)==12 | abs(pdgId)==14 | abs(pdgId)==16 | abs(pdgId)==511 | abs(pdgId)==521"
        )
    )

    # Gen Isolation: Calculate isolation for gen-level particles
    myGenIso = cms.EDProducer("GenPartIsoProducer",
        genPart = cms.InputTag("myFinalGenParticles"),
        packedGenPart = cms.InputTag("packedGenParticles"),
        additionalPdgId = cms.int32(22),
    )

    # Reco-to-Gen Matching: Match selected muons to gen-level muons
    muonGenMatch = cms.EDProducer("MCMatcher",
        src         = cms.InputTag("selectedMuons"),
        matched     = cms.InputTag("myFinalGenParticles"),
        mcPdgId     = cms.vint32(13),
        mcStatus    = cms.vint32(1),
        checkCharge = cms.bool(True),
        maxDPtRel   = cms.double(0.5),
        maxDeltaR   = cms.double(0.3),
        resolveAmbiguities    = cms.bool(True),
        resolveByMatchQuality = cms.bool(True),
    )

    # Embed matching results into the muon collection
    muonsWithMatch = cms.EDProducer("MuonMatchEmbedder",
        src      = cms.InputTag("selectedMuons"),
        matching = cms.InputTag("muonGenMatch")
    )

# --- 3. CANDIDATE BUILDING & TREE CONSTRUCTION ---

# Define muon source based on MC/Data
muonSrc = cms.InputTag("muonsWithMatch") if isMC else cms.InputTag("selectedMuons")

# Tau Candidate Builder: Perform vertex fitting for the 2Mu + 1Trk system
tau2mu1trBuilder = cms.EDProducer("Tau2Mu1TrkBuilder",
    muons    = muonSrc,
    tracks   = cms.InputTag("selectedTracks"),
    vertices = cms.InputTag("offlineSlimmedPrimaryVerticesWithBS"),
    beamSpot = cms.InputTag("offlineBeamSpot"),
    candidates = cms.InputTag("packedPFCandidates"),
)

# BPH Muon Selector: Add trigger matching information to muons
muonBPH = cms.EDProducer("MuonTriggerSelector",
    muonCollection = muonSrc,
    bits           = cms.InputTag("TriggerResults", "", "HLT"),
    prescales      = cms.InputTag("patTrigger"),
    objects        = cms.InputTag("slimmedPatTrigger"),
    maxdR_matching = cms.double(0.3), 
    muonSelection  = cms.string("pt > 2.0"), 
    HLTPaths       = HLT_path_list,
)

# --- 4. FLAT TABLES DEFINITION (NanoAOD Output) ---

# Tau Table: Stores triplet properties and vertex mass
tau2mu1trTable = cms.EDProducer("SimpleCompositeCandidateFlatTableProducer",
    src = cms.InputTag("tau2mu1trBuilder"),
    name = cms.string("Tau2MuTrk"),
    variables = cms.PSet(
        # Standard P4
        pt      = Var("pt", float),
        eta     = Var("eta", float),
        phi     = Var("phi", float),
        charge  = Var("charge", int),
        
        # Vertex Info
        mass    = Var("userFloat('sv_mass')", float, doc="Fitted invariant mass"),
        prob    = Var("userFloat('sv_prob')", float, doc="SV fit probability"),
        chi2    = Var("userFloat('sv_chi2')", float),
        ndof    = Var("userFloat('sv_ndof')", float),
        
        # Vertex Positions
        vx      = Var("userFloat('sv_x')", float),
        vy      = Var("userFloat('sv_y')", float),
        vz      = Var("userFloat('sv_z')", float),
        pvx     = Var("userFloat('pv_x')", float),
        pvy     = Var("userFloat('pv_y')", float),
        pvz     = Var("userFloat('pv_z')", float),
        
        # Flight Distance & Displacement
        flightDist    = Var("userFloat('flightDist')", float),
        flightDistSig = Var("userFloat('flightDistSig')", float),
        distXY        = Var("userFloat('distXY')", float),
        distXYSig     = Var("userFloat('distXYSig')", float),
        distBS        = Var("userFloat('flightDistBS')", float),
        
        # Refitted Kinematics
        refit_mu1_pt = Var("userFloat('refit_mu1_pt')", float),
        refit_mu2_pt = Var("userFloat('refit_mu2_pt')", float),
        refit_tr_pt  = Var("userFloat('refit_tr_pt')", float),
        
        # Impact Parameters
        dxy_mu1 = Var("userFloat('dxy_mu1')", float),
        dxy_mu2 = Var("userFloat('dxy_mu2')", float),
        dxy_tr  = Var("userFloat('dxy_tr')", float),
    )
)

# Muon Table: Stores muon kinematics and gen-matching
TrgMatchMuonTable = cms.EDProducer("SimplePATMuonFlatTableProducer",
    src  = cms.InputTag("muonBPH", "SelectedMuons"),
    name = cms.string("Muon"),
    variables = cms.PSet(
        # --- Kinematics ---
        pt     = Var("pt", float, precision=12),
        eta    = Var("eta", float, precision=12),
        phi    = Var("phi", float, precision=12),
        mass   = Var("mass", float, precision=12),
        charge = Var("charge", int),

        # --- Impact Parameters (DXY, DZ) ---
        # Usiamo i metodi standard di pat::Muon che non richiedono UserFloat extra
        dxy    = Var("dB('PV2D')", float, doc="dxy (with sign) wrt PV[0]", precision=12),
        dxyErr = Var("edB('PV2D')", float, doc="dxy uncertainty", precision=12),
        dz     = Var("dB('PVDZ')", float, doc="dz (with sign) wrt PV[0]", precision=12),
        dzErr  = Var("abs(edB('PVDZ'))", float, doc="dz uncertainty", precision=12),
        ip3d   = Var("abs(dB('PV3D'))", float, doc="3D impact parameter significance"),

        # --- Identification & Quality ---
        isPF     = Var("isPFMuon", bool),
        isGlobal = Var("isGlobalMuon", bool),
        isTracker= Var("isTrackerMuon", bool),
        isLoose  = Var("passed('CutBasedIdLoose')", bool),
        isMedium = Var("passed('CutBasedIdMedium')", bool),
        isSoft   = Var("passed('SoftCutBasedId')", bool),
        
        # --- Trigger & Custom ---
        isTriggering = Var("userInt('isTriggering')", bool),
        trgDR        = Var("userFloat('trgDR')", float),
        trgDPT       = Var("userFloat('trgDPT')", float),
        genPartPdgId = Var("userInt('mcMatch')" if isMC else "0", int),
        
        # --- Isolation (Standard) ---
        # Queste funzionano quasi sempre perché calcolate dai depositi nel rivelatore
        pfRelIso03_all = Var("(pfIsolationR03().sumChargedHadronPt + max(pfIsolationR03().sumNeutralHadronEt + pfIsolationR03().sumPhotonEt - pfIsolationR03().sumPUPt/2,0.0))/pt", float),
        pfRelIso04_all = Var("(pfIsolationR04().sumChargedHadronPt + max(pfIsolationR04().sumNeutralHadronEt + pfIsolationR04().sumPhotonEt - pfIsolationR04().sumPUPt/2,0.0))/pt", float),
        
        ## Specific Trigger path matching info
        HLT_DoubleMu3_Trk_Tau3mu = Var("userInt('HLT_DoubleMu3_Trk_Tau3mu')", int, doc="Matched to HLT_DoubleMu3_Trk_Tau3mu"),
        HLT_DoubleMu3_TkMu_DsTau3Mu_v = Var("userInt('HLT_DoubleMu3_TkMu_DsTau3Mu_v')", int, doc="Matched to HLT_DoubleMu3_TkMu_DsTau3Mu_v"),
        HLT_DoubleMu3_Trk_Tau3mu_NoL1Mass_v = Var("userInt('HLT_DoubleMu3_Trk_Tau3mu_NoL1Mass_v')", int, doc="Matched to HLT_DoubleMu3_Trk_Tau3mu_NoL1Mass_v"),
        HLT_DoubleMu4_3_LowMass_v = Var("userInt('HLT_DoubleMu4_3_LowMass_v')", int, doc="Matched to HLT_DoubleMu4_3_LowMass_v"),
        HLT_DoubleMu4_LowMass_Displaced_v = Var("userInt('HLT_DoubleMu4_LowMass_Displaced_v')", int, doc="Matched to HLT_DoubleMu4_LowMass_Displaced_v"),
    )
)

# --- Track Table: Stores comprehensive track parameters for PFCandidates ---
trackTable = cms.EDProducer("SimplePFCandidateFlatTableProducer",
    src = cms.InputTag("selectedTracks"),
    name = cms.string("Track"),
    variables = cms.PSet(
        # Kinematics
        pt     = Var("pt", float, precision=12),
        eta    = Var("eta", float, precision=12),
        phi    = Var("phi", float, precision=12),
        mass   = Var("mass", float, precision=10),
        charge = Var("charge", int),
        
        # Track Quality and Impact Parameters
        dz      = Var("dz", float, precision=10, doc="longitudinal impact parameter with respect to PV"),
        dxy     = Var("dxy", float, precision=10, doc="transverse impact parameter with respect to PV"),
        dzErr   = Var("dzError", float, precision=10),
        dxyErr  = Var("dxyError", float, precision=10),
        
        # Track Reconstruction Details
        lostInnerHits = Var("lostInnerHits", int, doc="number of lost inner hits"),
        numberOfPixelHits = Var("numberOfPixelHits", int, doc="number of valid pixel hits"),
        numberOfHits = Var("numberOfHits", int, doc="number of valid hits"),
        trackHighPurity = Var("trackHighPurity", bool, doc="track is marked as high purity"),
        
        # Isolation / Environment
        pdgId = Var("pdgId", int, doc="PDG identifier"),
    )
)

l1TableTau3Mu = cms.EDProducer("myL1TableProducer",
    src = cms.InputTag("gtStage2Digis"),
    name = cms.string("L1Seed"),
    doc = cms.string("L1 seeds"),
    extension = cms.bool(False), # <--- AGGIUNGI QUESTA RIGA
    seeds = cms.vstring(
        "L1_TripleMu_5SQ_3SQ_0_DoubleMu_5_3_SQ_OS_Mass_Max9",
        "L1_DoubleMu0er1p4_SQ_OS_dR_Max1p4",
        "L1_DoubleMu0er1p5_SQ_OS_dR_Max1p4",
        "L1_DoubleMu4_SQ_OS_dR_Max1p2",
        "L1_DoubleMu4p5_SQ_OS_dR_Max1p2",
        "L1_TripleMu_5SQ_3SQ_0OQ_DoubleMu_5_3_SQ_OS_Mass_Max9",
        "L1_DoubleMu0er2p0_SQ_OS_dEta_Max1p6",
        "L1_DoubleMu0er2p0_SQ_OS_dEta_Max1p5",
        "L1_TripleMu_2SQ_1p5SQ_0OQ_Mass_Max12",
        "L1_TripleMu_3SQ_2p5SQ_0OQ_Mass_Max12"
    )
)

# Vertex Table
pvTable = cms.EDProducer("SimpleVertexFlatTableProducer",
    src = cms.InputTag("offlineSlimmedPrimaryVerticesWithBS"),
    name = cms.string("PV"),
    variables = cms.PSet(
        x = Var("x", float, precision=10),
        y = Var("y", float, precision=10),
        z = Var("z", float, precision=10),
        chi2 = Var("chi2", float, precision=8),
    )
)

# Gen Particle Table: Stores MC truth information (Only if isMC)
if isMC:
    myGenParticleTable = simpleGenParticleFlatTableProducer.clone(
        src = cms.InputTag("myFinalGenParticles"),
        name= cms.string("GenPart"),
        externalVariables = cms.PSet(
            iso = ExtVar(cms.InputTag("myGenIso"), float, precision=8, doc="Gen Isolation"),
        ),
        variables = cms.PSet(
            pt               = Var("pt",  float),
            phi              = Var("phi", float),
            eta              = Var("eta",  float),
            mass             = Var("mass",  float),
            pdgId            = Var("pdgId", int),
            status           = Var("status", int),
            genPartIdxMother = Var("?numberOfMothers>0?motherRef(0).key():-1", "int16"),
        )
    )

# --- 5. FINAL EXECUTION SEQUENCE ---

# Filter and selection path (applied to every event)
tau2mu1trSequence = cms.Sequence(
    hltFilter +
    selectedMuons +
    TwoMuonsFilter +
    selectedTracks +
    oneTrackFilter +
    DiMuonCand +
    DiMuonCandFilter +
    TwoMuonsOneTrackCand +
    tauCountFilter
)

# MC-specific modules
if isMC:
    tau2mu1trSequence += (
        myFinalGenParticles +
        myGenIso +
        muonGenMatch +
        muonsWithMatch
    )

# Candidate construction and table filling
tau2mu1trSequence += (
    tau2mu1trBuilder +
    tau2mu1trTable +
    muonBPH +
    TrgMatchMuonTable +
    trackTable +
    l1TableTau3Mu +
    pvTable
)

# Append Gen Table if MC
if isMC:
    tau2mu1trSequence += myGenParticleTable