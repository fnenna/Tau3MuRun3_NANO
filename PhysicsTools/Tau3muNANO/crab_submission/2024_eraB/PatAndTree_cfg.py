import FWCore.ParameterSet.Config as cms
from Configuration.StandardSequences.Eras import eras
import FWCore.ParameterSet.VarParsing as VarParsing

# --- 1. CONFIGURAZIONE PARAMETRI ---
options = VarParsing.VarParsing('analysis')
options.register('isMC', False, 
                 VarParsing.VarParsing.multiplicity.singleton, 
                 VarParsing.VarParsing.varType.bool, 
                 "True se MC, False se Data")
options.parseArguments()

isMC = options.isMC
# 1. Definisci il processo (Run3 per il 2022/2026)
process = cms.Process('NANO', eras.Run3)

# 2. Servizi Standard
process.load("FWCore.MessageService.MessageLogger_cfi")
process.load("Configuration.StandardSequences.GeometryRecoDB_cff")
process.load("Configuration.StandardSequences.MagneticField_cff")
process.load("Configuration.StandardSequences.FrontierConditions_GlobalTag_cff")
process.load("TrackingTools.TransientTrack.TransientTrackBuilder_cfi")

# 3. Imposta la Global Tag (cambiala in base al tuo dataset!)
from Configuration.AlCa.GlobalTag import GlobalTag
if isMC:
    # Esempio per MC 2024
    process.GlobalTag = GlobalTag(process.GlobalTag, '140X_mcRun3_2024_realistic_v26', '')
else:
    # Esempio per Data 2024 (cambiala in base all'era specifica!)
    process.GlobalTag = GlobalTag(process.GlobalTag, '140X_dataRun3_v20', '')

output_name = "dsphipi_output_MC.root" if isMC else "dsphipi_output_Data.root"

# 4. Numero di eventi
process.maxEvents = cms.untracked.PSet(input = cms.untracked.int32(1000))

# 5. File di Input
process.source = cms.Source("PoolSource",
    fileNames = cms.untracked.vstring(
    #'root://xrootd-cms.infn.it//store/mc/Run3Summer23MiniAODv4/DstoPhiPi_Phito2Mu_MuFilter_TuneCP5_13p6TeV_pythia8-evtgen/MINIAODSIM/130X_mcRun3_2023_realistic_v14-v2/2810000/23794a69-978d-4aa5-83c9-60265065cc5b.root'
      #'root://xrootd-cms.infn.it//store/mc/Run3Summer22EEMiniAODv4/BsToJpsiPhi_JMM_PhiMM_MuFilter_SoftQCDnonD_TuneCP5_13p6TeV-pythia8-evtgen/MINIAODSIM/130X_mcRun3_2022_realistic_postEE_v6-v2/50000/43d2b67f-908f-4c7f-952e-22d02e1852a5.root'
      'root://xrootd-cms.infn.it///store/data/Run2022C/ParkingDoubleMuonLowMass0/MINIAOD/PromptReco-v1/000/355/863/00000/389f9ca1-f590-4691-b7f2-41e0146a8a79.root'
    )
)

# 6. Carica la sequenza 2mu + 1trk
# Assicurati che il file dove abbiamo messo il builder si chiami 'Tau2Mu1Trk_cff.py' 
# e sia nel path indicato sotto
process.load("PhysicsTools.Tau3muNANO.DsPhiPi_builder_cff")
process.load("SimGeneral.HepPDTESSource.pythiapdt_cfi") ##if isMC

# Se vuoi cambiare isMC al volo senza modificare il file cff, puoi farlo qui:
# process.isMC = cms.bool(True) 

# 7. File di output NanoAOD
process.out = cms.OutputModule("NanoAODOutputModule",
    fileName = cms.untracked.string(output_name),
    SelectEvents = cms.untracked.PSet(
        SelectEvents = cms.vstring('p') 
    ),
    outputCommands = cms.untracked.vstring(
        "drop *",
        "keep nanoaodFlatTable_*_*_*", # Tiene le tabelle che abbiamo creato
    ),
    compressionLevel = cms.untracked.int32(9),
    compressionAlgorithm = cms.untracked.string("ZLIB"),
)

# 8. Path
# 'tau2mu1trSequence' è il nome della sequenza finale che abbiamo definito nel cff
process.p = cms.Path(process.tau2mu1trSequence)
process.endp = cms.EndPath(process.out)

# Report ogni 100 eventi per non intasare il log
process.MessageLogger.cerr.FwkReport.reportEvery = 100