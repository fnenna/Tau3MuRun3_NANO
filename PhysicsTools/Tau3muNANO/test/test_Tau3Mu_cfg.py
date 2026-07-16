import FWCore.ParameterSet.Config as cms
from Configuration.StandardSequences.Eras import eras
import FWCore.ParameterSet.VarParsing as VarParsing
from PhysicsTools.Tau3muNANO.Tau3mu_builder_cff import setupTau3Mu

options = VarParsing.VarParsing('analysis')
options.register('isMC', True, 
                 VarParsing.VarParsing.multiplicity.singleton, 
                 VarParsing.VarParsing.varType.bool, 
                 "True if MC, False if Data")
options.parseArguments()

isMC = options.isMC
process = cms.Process('NANO', eras.Run3)

process.load("FWCore.MessageService.MessageLogger_cfi")
process.load("Configuration.StandardSequences.GeometryRecoDB_cff")
process.load("Configuration.StandardSequences.MagneticField_cff")
process.load("Configuration.StandardSequences.FrontierConditions_GlobalTag_cff")
process.load("PhysicsTools.NanoAOD.nano_cff")
process.load("TrackingTools.TransientTrack.TransientTrackBuilder_cfi")

from Configuration.AlCa.GlobalTag import GlobalTag
if isMC:
    process.GlobalTag = GlobalTag(process.GlobalTag, '140X_mcRun3_2024_realistic_v26', '')
else:
    process.GlobalTag = GlobalTag(process.GlobalTag, '140X_dataRun3_v4', '')

output_name = "tau3mu_output_MC.root" if isMC else "tau3mu_output_Data.root"

process.maxEvents = cms.untracked.PSet(input = cms.untracked.int32(1000))

process.source = cms.source = cms.Source("PoolSource",
    fileNames = cms.untracked.vstring(
        'root://xrootd-cms.infn.it//store/mc/RunIII2024Summer24MiniAOD/BdtoTau-Tauto3Mu_Fil-3Mu_TuneCP5_13p6TeV_pythia8-evtgen/MINIAODSIM/140X_mcRun3_2024_realistic_v26-v8/120000/029d6839-0ddd-426e-a47c-2a1452c22d2c.root')
)

process.load("PhysicsTools.Tau3muNANO.Tau3mu_builder_cff")
process.load("SimGeneral.HepPDTESSource.pythiapdt_cfi") ##if isMC

setupTau3Mu(process, isMC)

process.out = cms.OutputModule("NanoAODOutputModule",
    fileName = cms.untracked.string(output_name),
    SelectEvents = cms.untracked.PSet(
        SelectEvents = cms.vstring('p')
    ),
    outputCommands = cms.untracked.vstring(
        "drop *",
        "keep nanoaodFlatTable_*_*_*",
    ),
    compressionLevel = cms.untracked.int32(9),
    compressionAlgorithm = cms.untracked.string("ZLIB"),
)

process.p = cms.Path(process.tau3muSequence)
process.endp = cms.EndPath(process.out)

process.MessageLogger.cerr.FwkReport.reportEvery = 100