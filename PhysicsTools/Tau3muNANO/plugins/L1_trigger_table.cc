#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/stream/EDProducer.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "DataFormats/NanoAOD/interface/FlatTable.h"
#include "DataFormats/L1TGlobal/interface/GlobalAlgBlk.h"
#include "CondFormats/DataRecord/interface/L1TUtmTriggerMenuRcd.h"
#include "CondFormats/L1TObjects/interface/L1TUtmTriggerMenu.h"
#include "FWCore/Framework/interface/ESHandle.h"

class myL1TableProducer : public edm::stream::EDProducer<> {
public:
    explicit myL1TableProducer(const edm::ParameterSet& iConfig) :
        token_(consumes<GlobalAlgBlkBxCollection>(iConfig.getParameter<edm::InputTag>("src"))),
        utmToken_(esConsumes<L1TUtmTriggerMenu, L1TUtmTriggerMenuRcd>()),
        name_(iConfig.getParameter<std::string>("name")),
        doc_(iConfig.getParameter<std::string>("doc")),
        extension_(iConfig.getParameter<bool>("extension")),
        listOfSeeds_(iConfig.getParameter<std::vector<std::string>>("seeds")) {
        produces<nanoaod::FlatTable>();
    }

    void produce(edm::Event& iEvent, const edm::EventSetup& iSetup) override {
        auto const& results = iEvent.get(token_);
        auto const& menuHandle = iSetup.getHandle(utmToken_);
        const L1TUtmTriggerMenu* menu = menuHandle.isValid() ? menuHandle.product() : nullptr;

        std::vector<bool> decisions;
        if (!results.isEmpty(0)) {
            decisions = results.at(0, 0).getAlgoDecisionFinal();
        }

        // Creiamo la tabella per l'evento corrente (finirà in Events)
        auto tab = std::make_unique<nanoaod::FlatTable>(1, name_, true, extension_); 
        tab->setDoc(doc_);

        for (const auto& seedName : listOfSeeds_) {
            uint8_t pass = 0;
            if (menu && !decisions.empty()) {
                auto const& algoMap = menu->getAlgorithmMap();
                auto it = algoMap.find(seedName);
                if (it != algoMap.end()) {
                    unsigned int index = it->second.getIndex();
                    if (index < decisions.size()) pass = (decisions[index] ? 1 : 0);
                }
            }
            // addColumnValue è il metodo corretto per tabelle singleton in Events
            tab->addColumnValue<uint8_t>(seedName, pass, "L1 bit for " + seedName);
        }
        iEvent.put(std::move(tab));
    }

private:
    const edm::EDGetTokenT<GlobalAlgBlkBxCollection> token_;
    const edm::ESGetToken<L1TUtmTriggerMenu, L1TUtmTriggerMenuRcd> utmToken_;
    const std::string name_;
    const std::string doc_;
    const bool extension_;
    const std::vector<std::string> listOfSeeds_;
};

#include "FWCore/Framework/interface/MakerMacros.h"
DEFINE_FWK_MODULE(myL1TableProducer);