import FWCore.ParameterSet.Config as cms
from PhysicsTools.NanoAOD.common_cff import *
from PhysicsTools.NanoAOD.simpleGenParticleFlatTableProducer_cfi import simpleGenParticleFlatTableProducer
from PhysicsTools.NanoAOD.muons_cff import muonTable
from PhysicsTools.NanoAOD.globalVariablesTableProducer_cfi import globalVariablesTableProducer

isMC = False

print(f"--- Running Tau3Mu Analysis in {'MC' if isMC else 'DATA'} mode ---")

# --- 1. EVENT FILTERS (HLT & SKIMMING) ---

HLT_path_list = cms.vstring(
        "HLT_DoubleMu3_Trk_Tau3mu", 
        "HLT_DoubleMu3_TkMu_DsTau3Mu_v", 
        "HLT_DoubleMu3_Trk_Tau3mu_NoL1Mass_v", 
        "HLT_DoubleMu4_3_LowMass_v", 
        "HLT_DoubleMu4_LowMass_Displaced_v"
    )

my_l1_seeds = [
    "L1_DoubleMu0_er1p5_SQ_OS_dR_Max1p4",
    "L1_DoubleMu4_SQ_OS_dR_Max1p2",
    "L1_DoubleMu4p5_SQ_OS_dR_Max1p2",
    "L1_TripleMu_5_3_3",
    "L1_TripleMu_5_3p5_2p5_DoubleMu_5_2p5_OS_dR_Max5",
]

# HLT Filter: Select events passing specific trigger paths
hltFilter = cms.EDFilter("HLTHighLevel",
    HLTPaths = cms.vstring([path + "*" for path in HLT_path_list]),
    throw = cms.bool(False)
)

# Muon selection for the Triplet
selectedMuons = cms.EDFilter("PATMuonSelector",
    src = cms.InputTag("slimmedMuons"),
    cut = cms.string("pt > 2.0 && abs(eta) < 2.4 && (innerTrack().isNonnull) && (charge!=0) && (innerTrack().hitPattern().numberOfValidPixelHits()>0)"),
    filter = cms.bool(True)
)

# Preliminary Filter: Events must have at least 3 muons passing cuts
threeMuonsFilter = cms.EDFilter("CandViewCountFilter",
    src       = cms.InputTag("selectedMuons"),
    minNumber = cms.uint32(3)
)

# Technical Skim: Combiner for 3 Muons (Charge Requirement)
ThreeMuonsCand = cms.EDProducer("CandViewShallowCloneCombiner",
    checkCharge = cms.bool(False),
    cut = cms.string('(abs(charge)==1)'), # Require total charge |Q| = 1
    decay = cms.string("selectedMuons selectedMuons selectedMuons")
) 

ThreeMuonsCandFilter = cms.EDFilter("CandViewCountFilter",
    src = cms.InputTag("ThreeMuonsCand"),
    minNumber = cms.uint32(1)
)

# --- 2. MONTE CARLO MODULES (Conditional on isMC) ---

if isMC:
    # Filter GenParticles to keep only Taus and their Muon daughters
    myFinalGenParticles = cms.EDProducer("GenParticlePruner",
        src = cms.InputTag("prunedGenParticles"),
        select = cms.vstring(
            "drop *",
            "keep abs(pdgId)==13 | abs(pdgId)==15 | abs(pdgId)==11 | abs(pdgId)==211 | abs(pdgId)==321 | abs(pdgId)==431 | abs(pdgId)==12 | abs(pdgId)==14 | abs(pdgId)==16 | abs(pdgId)==511 | abs(pdgId)==521" #| abs(pdgId)==333
        )
    )

    # Gen Isolation calculation
    myGenIso = cms.EDProducer("GenPartIsoProducer",
        genPart = cms.InputTag("myFinalGenParticles"),
        packedGenPart = cms.InputTag("packedGenParticles"),
        additionalPdgId = cms.int32(22),
    )

    # Reco-to-Gen Matching
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

    # Embed matching info into muons
    muonsWithMatch = cms.EDProducer("MuonMatchEmbedder",
        src      = cms.InputTag("selectedMuons"),
        matching = cms.InputTag("muonGenMatch")
    )

# Determine the correct Muon source for subsequent modules
muonSrc = cms.InputTag("muonsWithMatch") if isMC else cms.InputTag("selectedMuons")

# --- 3. CANDIDATE BUILDING & TREE CONSTRUCTION ---

# Tau3Mu Signal Builder
tau3muBuilder = cms.EDProducer("Tau3MuBuilder",
    src = muonSrc,
    vertices = cms.InputTag("offlineSlimmedPrimaryVerticesWithBS"),
    candidates = cms.InputTag("packedPFCandidates"),
    beamSpot = cms.InputTag("offlineBeamSpot"),
    genParticles = cms.InputTag("myFinalGenParticles"),
)

# BPH Muon Selector for Trigger Matching
muonBPH = cms.EDProducer("MuonTriggerSelector",
    muonCollection = muonSrc,                                                
    bits           = cms.InputTag("TriggerResults", "", "HLT"),
    prescales      = cms.InputTag("patTrigger"),
    objects        = cms.InputTag("slimmedPatTrigger"),
    maxdR_matching = cms.double(0.3),
    muonSelection  = cms.string("pt > 2.0"), 
    HLTPaths       = HLT_path_list
)


# --- 4. FLAT TABLES DEFINITION (Output Tree) ---

# Tau3Mu Table: Signal variables
tau3muTable = cms.EDProducer("SimpleCompositeCandidateFlatTableProducer",
    src = cms.InputTag("tau3muBuilder"),
    name = cms.string("Tau3Mu"),
    doc = cms.string("Tau to 3Mu candidates"),
    variables = cms.PSet(
    # Standard P4 del tripletto
    pt      = Var("pt", float),
    eta     = Var("eta", float),
    phi     = Var("phi", float),
    charge  = Var("charge", int),

    # --- Cinematica Muone 1 ---
    mu1_pt  = Var("userFloat('mu1_pt')", float, doc="pt of the first muon"),
    mu1_eta = Var("userFloat('mu1_eta')", float),
    mu1_phi = Var("userFloat('mu1_phi')", float),

    # --- Cinematica Muone 2 ---
    mu2_pt  = Var("userFloat('mu2_pt')", float, doc="pt of the second muon"),
    mu2_eta = Var("userFloat('mu2_eta')", float),
    mu2_phi = Var("userFloat('mu2_phi')", float),

    # --- Cinematica Traccia ---
    tr_pt   = Var("userFloat('tr_pt')", float, doc="pt of the track"),
    tr_eta  = Var("eta", float), # La traccia eredita la coordinata dal candidato se non salvata esplicitamente
    tr_phi  = Var("phi", float),

    # Indici originali
    mu1_idx = Var("userInt('mu1_idx')", int),
    mu2_idx = Var("userInt('mu2_idx')", int),
    tr_idx  = Var("userInt('tr_idx')", int),
    
    # Vertex Info
    mass    = Var("userFloat('sv_mass')", float, doc="Fitted invariant mass"),
    prob    = Var("userFloat('sv_prob')", float, doc="SV fit probability"),
    chi2    = Var("userFloat('sv_chi2')", float),
    ndof    = Var("userFloat('sv_ndof')", float),
    
    # Vertex Positions
    sv_x    = Var("userFloat('sv_x')", float),
    sv_y    = Var("userFloat('sv_y')", float),
    sv_z    = Var("userFloat('sv_z')", float),
    pv_x    = Var("userFloat('pv_x')", float),
    pv_y    = Var("userFloat('pv_y')", float),
    pv_z    = Var("userFloat('pv_z')", float),
    
    # Flight Distance & Displacement
    flightDist    = Var("userFloat('flightDist')", float),
    flightDistSig = Var("userFloat('flightDistSig')", float),
    lxy_pv        = Var("userFloat('lxy_pv')", float),
    distXYSig     = Var("userFloat('distXYSig')", float),
    distBS        = Var("userFloat('flightDistBS')", float),
    
    # Refitted Kinematics (al vertice SV)
    refit_mu1_pt = Var("userFloat('refit_mu1_pt')", float),
    refit_mu2_pt = Var("userFloat('refit_mu2_pt')", float),
    refit_tr_pt  = Var("userFloat('refit_tr_pt')", float),
    
    # Impact Parameters (rispetto al PV refittato)
    dxy_mu1 = Var("userFloat('dxy_mu1')", float),
    dxy_mu2 = Var("userFloat('dxy_mu2')", float),
    dxy_tr  = Var("userFloat('dxy_tr')", float),
    
    # Isolamento e Angoli
    mindca_iso = Var("userFloat('mindca_iso')", float),
    rel_iso    = Var("userFloat('relative_iso')", float),
    pointingAngle = Var("userFloat('pointingAngle')", float),

    # High Purity Flags
    mu1_hp = Var("userInt('mu1_innerTrk_hp')", int),
    mu2_hp = Var("userInt('mu2_innerTrk_hp')", int),
    tr_hp  = Var("userInt('tr_innerTrk_hp')", int),

    # --- Muon Matching (Solo per Muone 1 e 2) ---
    # Stazione 1
    mu1_match1_dX = Var("userFloat('mu1_match1_dX')", float),
    mu1_match1_pullX = Var("userFloat('mu1_match1_pullX')", float),
    mu2_match1_dX = Var("userFloat('mu2_match1_dX')", float),
    mu2_match1_pullX = Var("userFloat('mu2_match1_pullX')", float),
    
    # Stazione 2
    mu1_match2_dX = Var("userFloat('mu1_match2_dX')", float),
    mu1_match2_pullX = Var("userFloat('mu1_match2_pullX')", float),
    mu2_match2_dX = Var("userFloat('mu2_match2_dX')", float),
    mu2_match2_pullX = Var("userFloat('mu2_match2_pullX')", float),
    )
)

# Muon Table: BPH specialized Muons
TrgMatchMuonTable = cms.EDProducer("SimplePATMuonFlatTableProducer",
    src  = cms.InputTag("muonBPH", "SelectedMuons"),
    name = cms.string("Muon"),
    variables = cms.PSet(
        # --- Kinematics ---
        p     = Var("p", float, precision=12),
        pt     = Var("pt", float, precision=12),
        eta    = Var("eta", float, precision=12),
        phi    = Var("phi", float, precision=12),
        mass   = Var("mass", float, precision=12),
        energy   = Var("energy", float, precision=12),
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
        
        mvaId = Var("mvaIDValue()", float, doc="MVA Soft ID"),
        softMva = Var("softMvaValue()", float),
        segmentCompatibility = Var("segmentCompatibility()", float),
        caloCompatibility = Var("caloCompatibility()", float),

        sumPt03 = Var("isolationR03().sumPt", float, doc="Tracker isolation sumPt in dR=0.3"),
        sumPt05 = Var("isolationR05().sumPt", float, doc="Tracker isolation sumPt in dR=0.5"),

        # Numero di tracce in un cono di 0.3
        nTracks03 = Var("isolationR03().nTracks", int, doc="Number of tracks in dR=0.3 tracker isolation cone"),
        nTracks05 = Var("isolationR05().nTracks", int, doc="Number of tracks in dR=0.5 tracker isolation cone"),
        # CombinedQuality Updated stats
        trkKink = Var("combinedQuality().trkKink", float),
        glbKink = Var("combinedQuality().glbKink", float),
        trkRelChi2 = Var("combinedQuality().trkRelChi2", float),
        staRelChi2 = Var("combinedQuality().staRelChi2", float),
        chi2LocalPosition = Var("combinedQuality().chi2LocalPosition", float),
        chi2LocalMomentum = Var("combinedQuality().chi2LocalMomentum", float),
        localDistance = Var("combinedQuality().localDistance", float),
        globalDeltaEtaPhi = Var("combinedQuality().globalDeltaEtaPhi", float),
        tightMatch = Var("combinedQuality().tightMatch", float),
        glbTrackProbability = Var("combinedQuality().glbTrackProbability", float),

        ## Specific Trigger path matching info
        HLT_DoubleMu3_Trk_Tau3mu = Var("userInt('HLT_DoubleMu3_Trk_Tau3mu')", int, doc="Matched to HLT_DoubleMu3_Trk_Tau3mu"),
        HLT_DoubleMu3_TkMu_DsTau3Mu_v = Var("userInt('HLT_DoubleMu3_TkMu_DsTau3Mu_v')", int, doc="Matched to HLT_DoubleMu3_TkMu_DsTau3Mu_v"),
        HLT_DoubleMu3_Trk_Tau3mu_NoL1Mass_v = Var("userInt('HLT_DoubleMu3_Trk_Tau3mu_NoL1Mass_v')", int, doc="Matched to HLT_DoubleMu3_Trk_Tau3mu_NoL1Mass_v"),
        HLT_DoubleMu4_3_LowMass_v = Var("userInt('HLT_DoubleMu4_3_LowMass_v')", int, doc="Matched to HLT_DoubleMu4_3_LowMass_v"),
        HLT_DoubleMu4_LowMass_Displaced_v = Var("userInt('HLT_DoubleMu4_LowMass_Displaced_v')", int, doc="Matched to HLT_DoubleMu4_LowMass_Displaced_v"),

        # --- Validation Flags ---
        isQValid = Var("isQualityValid()", bool, doc="Muon isQualityValid"),
        isTValid = Var("isTimeValid()", bool, doc="Muon isTimeValid"),
        isIsoValid = Var("isIsolationValid()", bool, doc="Muon isIsolationValid"),

        # --- Global Track Variables ---
        GLnormChi2 = Var("?globalTrack().isNonnull()?globalTrack().normalizedChi2():-99", float, doc="Global track normalized chi2"),
        GL_nValidMuHits = Var("?globalTrack().isNonnull()?globalTrack().hitPattern().numberOfValidMuonHits():-1", int, doc="Number of valid muon hits in global track"),

        # --- Tracker & Hit Pattern ---
        trkLayersWMeas = Var("?innerTrack().isNonnull()?innerTrack().hitPattern().trackerLayersWithMeasurement():-1", int),
        nValidTrackerHits = Var("?innerTrack().isNonnull()?innerTrack().hitPattern().numberOfValidTrackerHits():-1", int),
        nValidPixelHits = Var("?innerTrack().isNonnull()?innerTrack().hitPattern().numberOfValidPixelHits():-1", int),
        validMuonHitComb = Var("?globalTrack().isNonnull()?globalTrack().hitPattern().numberOfValidMuonHits():-1", int), # Spesso mappato così

        # --- Outer Track (Standalone Muon) ---
        outerTrk_P = Var("?outerTrack().isNonnull()?outerTrack().p():-99", float),
        outerTrk_Eta = Var("?outerTrack().isNonnull()?outerTrack().eta():-99", float),
        outerTrk_normChi2 = Var("?outerTrack().isNonnull()?outerTrack().normalizedChi2():-99", float),
        outerTrk_muStValidHits = Var("?outerTrack().isNonnull()?outerTrack().hitPattern().muonStationsWithValidHits():-1", int),

        # --- Inner Track (Tracker Track) ---
        innerTrk_P = Var("?innerTrack().isNonnull()?innerTrack().p():-99", float),
        innerTrk_Eta = Var("?innerTrack().isNonnull()?innerTrack().eta():-99", float),
        innerTrk_normChi2 = Var("?innerTrack().isNonnull()?innerTrack().normalizedChi2():-99", float),
        innerTrk_ValidFraction = Var("?innerTrack().isNonnull()?innerTrack().validFraction():-99", float),

        # --- Combined Quality & Compatibility ---
        QInnerOuter = Var("combinedQuality().updatedSta", bool), # Spesso usato come proxy per QInnerOuter
        cQ_uS = Var("combinedQuality().updatedSta", bool),
        cQ_tK = Var("combinedQuality().trkKink", float),
        cQ_gK = Var("combinedQuality().glbKink", float),
        cQ_tRChi2 = Var("combinedQuality().trkRelChi2", float),
        cQ_sRChi2 = Var("combinedQuality().staRelChi2", float),
        cQ_Chi2LP = Var("combinedQuality().chi2LocalPosition", float),
        cQ_Chi2LM = Var("combinedQuality().chi2LocalMomentum", float),
        cQ_lD = Var("combinedQuality().localDistance", float),
        cQ_gDEP = Var("combinedQuality().globalDeltaEtaPhi", float),
        cQ_tM = Var("combinedQuality().tightMatch", bool),
        cQ_gTP = Var("combinedQuality().glbTrackProbability", float),
        
        segmComp = Var("segmentCompatibility()", float),
        caloComp = Var("caloCompatibility()", float),
    )
)

# Track Table: Using PFCandidates
trackTable = cms.EDProducer("SimplePFCandidateFlatTableProducer",
    src = cms.InputTag("packedPFCandidates"),
    cut = cms.string("pt > 2.5 && abs(eta) < 2.4 && hasTrackDetails()"), 
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


triggerTableTau3Mu = cms.EDProducer("myTriggerTableProducer",
    l1Src = cms.InputTag("gtStage2Digis"),
    hltSrc = cms.InputTag("TriggerResults", "", "HLT"),
    name = cms.string("Trigger"), # Nome della tabella nel ROOT
    doc = cms.string("L1 and HLT bits for Tau3Mu analysis"),
    extension = cms.bool(False),
    l1Seeds = cms.vstring(
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
    ),
    hltPaths = HLT_path_list
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

# Gen Particle Table (MC Only)
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

# --- 5. EXECUTION SEQUENCE ---

# Filter Sequence
tau3muSequence = cms.Sequence(
    hltFilter +
    selectedMuons +
    threeMuonsFilter +
    ThreeMuonsCand +
    ThreeMuonsCandFilter
)

# Add MC modules if needed
if isMC:
    tau3muSequence += (
        myFinalGenParticles +
        myGenIso +
        muonGenMatch +
        muonsWithMatch
    )

# Building and Table sequence
tau3muSequence += (
    tau3muBuilder + 
    tau3muTable + 
    muonBPH +
    TrgMatchMuonTable +
    triggerTableTau3Mu +
    pvTable +
    trackTable
)

if isMC:
    tau3muSequence += myGenParticleTable