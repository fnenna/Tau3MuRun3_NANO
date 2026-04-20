import FWCore.ParameterSet.Config as cms
from Configuration.StandardSequences.Eras import eras

# 1. Definisci il processo usando l'era corretta (es. Run2 2018 o Run3)
process = cms.Process('TEST', eras.Run3)

# 2. Importa i servizi standard
process.load("FWCore.MessageService.MessageLogger_cfi")
process.load("Configuration.StandardSequences.GeometryRecoDB_cff")
process.load("Configuration.StandardSequences.MagneticField_cff")
process.load("Configuration.StandardSequences.FrontierConditions_GlobalTag_cff")
process.load("PhysicsTools.NanoAOD.nano_cff")
process.load("TrackingTools.TransientTrack.TransientTrackBuilder_cfi")


# 3. Imposta la Global Tag (cambiala in base al tuo dataset!)
from Configuration.AlCa.GlobalTag import GlobalTag
process.GlobalTag = GlobalTag(process.GlobalTag, '140X_mcRun3_2024_realistic_v26', '') 


# 4. Numero di eventi da processare (-1 per tutti)
process.maxEvents = cms.untracked.PSet(input = cms.untracked.int32(1000))

# 5. File di input (usa un file locale o un link redirector AAA)
process.source = cms.source = cms.Source("PoolSource",
    fileNames = cms.untracked.vstring('root://xrootd-cms.infn.it//store/mc/RunIII2024Summer24MiniAOD/BdtoTau-Tauto3Mu_Fil-3Mu_TuneCP5_13p6TeV_pythia8-evtgen/MINIAODSIM/140X_mcRun3_2024_realistic_v26-v8/120000/029d6839-0ddd-426e-a47c-2a1452c22d2c.root')
)

# 6. Carica il tuo Builder e la Tabella (assumendo siano nel file che abbiamo scritto prima)
# Se il codice è in un file chiamato 'PhysicsTools/BPHNano/python/tau3mu_cff.py'
process.load("PhysicsTools.Tau3muNANO.Tau3mu_builder_cff")

process.load("SimGeneral.HepPDTESSource.pythiapdt_cfi") ##if isMC
# 7. Definisci il file di output NanoAOD
process.out = cms.OutputModule("NanoAODOutputModule",
    fileName = cms.untracked.string("tau3mu_test_outputMC.root"),
    SelectEvents = cms.untracked.PSet(
        SelectEvents = cms.vstring('p') # 'p' deve essere il nome del tuo cms.Path
    ),
    outputCommands = cms.untracked.vstring(
        "drop *",
        "keep nanoaodFlatTable_*_*_*", # Tiene le tabelle che abbiamo creato
    ),
    compressionLevel = cms.untracked.int32(9),
    compressionAlgorithm = cms.untracked.string("ZLIB"),
)

# 8. Percorso di esecuzione (Path)
process.p = cms.Path(process.tau3muSequence)
process.endp = cms.EndPath(process.out)

# Opzionale: riduci il log per non intasare lo schermo
process.MessageLogger.cerr.FwkReport.reportEvery = 10