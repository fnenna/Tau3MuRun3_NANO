#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/stream/EDProducer.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "DataFormats/NanoAOD/interface/FlatTable.h"
#include "DataFormats/L1TGlobal/interface/GlobalAlgBlk.h"
#include "DataFormats/Common/interface/TriggerResults.h"
#include "FWCore/Common/interface/TriggerNames.h"
#include "CondFormats/DataRecord/interface/L1TUtmTriggerMenuRcd.h"
#include "CondFormats/L1TObjects/interface/L1TUtmTriggerMenu.h"
#include "FWCore/Framework/interface/ESHandle.h"

class myTriggerTableProducer : public edm::stream::EDProducer<> {
public:
    explicit myTriggerTableProducer(const edm::ParameterSet& iConfig) :
        l1Token_(consumes<GlobalAlgBlkBxCollection>(iConfig.getParameter<edm::InputTag>("l1Src"))),
        hltToken_(consumes<edm::TriggerResults>(iConfig.getParameter<edm::InputTag>("hltSrc"))),
        utmToken_(esConsumes<L1TUtmTriggerMenu, L1TUtmTriggerMenuRcd>()),
        name_(iConfig.getParameter<std::string>("name")),
        doc_(iConfig.getParameter<std::string>("doc")),
        extension_(iConfig.getParameter<bool>("extension")),
        l1Seeds_(iConfig.getParameter<std::vector<std::string>>("l1Seeds")),
        hltPaths_(iConfig.getParameter<std::vector<std::string>>("hltPaths")) {
        produces<nanoaod::FlatTable>();
    }

    void produce(edm::Event& iEvent, const edm::EventSetup& iSetup) override {
        // --- L1 Logic ---
        auto const& l1Results = iEvent.get(l1Token_);
        auto const& menuHandle = iSetup.getHandle(utmToken_);
        const L1TUtmTriggerMenu* menu = menuHandle.isValid() ? menuHandle.product() : nullptr;

        std::vector<bool> l1Decisions;
        if (!l1Results.isEmpty(0)) {
            l1Decisions = l1Results.at(0, 0).getAlgoDecisionFinal();
        }

        // --- HLT Logic ---
        auto const& hltResults = iEvent.get(hltToken_);
        auto const& hltNames = iEvent.triggerNames(hltResults);

        // Create Table
        auto tab = std::make_unique<nanoaod::FlatTable>(1, name_, true, extension_); 
        tab->setDoc(doc_);

        // Fill L1 Seeds
        for (const auto& seedName : l1Seeds_) {
            uint8_t pass = 0;
            if (menu && !l1Decisions.empty()) {
                auto const& algoMap = menu->getAlgorithmMap();
                auto it = algoMap.find(seedName);
                if (it != algoMap.end()) {
                    unsigned int index = it->second.getIndex();
                    if (index < l1Decisions.size()) pass = (l1Decisions[index] ? 1 : 0);
                }
            }
            tab->addColumnValue<uint8_t>(seedName, pass, "L1 bit: " + seedName);
        }

        // Fill HLT Paths
        for (const auto& pathName : hltPaths_) {
            uint8_t pass = 0;
            // Cerchiamo il path (gestisce la risoluzione del nome se passi il nome completo)
            unsigned int index = hltNames.triggerIndex(pathName);
            
            if (index < hltNames.size()) {
                pass = hltResults.accept(index) ? 1 : 0;
            } else {
                // Se non lo trova, prova a cercare con wildcard parziale (es. HLT_DoubleMu3_v)
                for (unsigned int i = 0; i < hltNames.size(); ++i) {
                    if (hltNames.triggerName(i).find(pathName) == 0) { // Inizia con...
                        if (hltResults.accept(i)) pass = 1;
                        break;
                    }
                }
            }
            tab->addColumnValue<uint8_t>(pathName, pass, "HLT bit: " + pathName);
        }

        iEvent.put(std::move(tab));
    }

private:
    const edm::EDGetTokenT<GlobalAlgBlkBxCollection> l1Token_;
    const edm::EDGetTokenT<edm::TriggerResults> hltToken_;
    const edm::ESGetToken<L1TUtmTriggerMenu, L1TUtmTriggerMenuRcd> utmToken_;
    const std::string name_;
    const std::string doc_;
    const bool extension_;
    const std::vector<std::string> l1Seeds_;
    const std::vector<std::string> hltPaths_;
};

#include "FWCore/Framework/interface/MakerMacros.h"
DEFINE_FWK_MODULE(myTriggerTableProducer);