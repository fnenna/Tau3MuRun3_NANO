from CRABClient.UserUtilities import config, getUsername
config = config()

config.General.requestName = 'SkimDsPhiPi_2024eraB_stream7_Mini_v4'
config.General.workArea = 'crab_projects'
config.General.transferOutputs = True
config.General.transferLogs = False

config.JobType.pluginName = 'Analysis'

config.JobType.psetName = '/eos/home-f/fnenna/tau3mu_run3/CMSSW_15_0_0/src/PhysicsTools/Tau3muNANO/crab_submission/2024_eraB/PatAndTree_cfg.py'
config.JobType.pyCfgParams = ['isMC=False']

config.Data.inputDataset = '/ParkingDoubleMuonLowMass7/Run2024B-PromptReco-v1/MINIAOD'
config.Data.allowNonValidInputDataset = True
config.Data.inputDBS = 'global'
config.Data.splitting = 'LumiBased'
config.Data.unitsPerJob = 50
config.Data.lumiMask = 'https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions24/2024B_Golden.json'
#config.Data.publication = True
config.Data.outputDatasetTag = 'SkimDsPhiPi_2024eraB_stream7_Mini_v4'
config.JobType.allowUndistributedCMSSW = True 
config.Site.storageSite = 'T2_IT_Bari'
config.Site.ignoreGlobalBlacklist  = True
