#include "PhysicsTools/NanoAOD/interface/SimpleFlatTableProducer.h"
#include "DataFormats/PatCandidates/interface/CompositeCandidate.h"
#include "FWCore/Framework/interface/MakerMacros.h"

// Definiamo esplicitamente il tipo per pat::CompositeCandidate
typedef SimpleFlatTableProducer<pat::CompositeCandidate> SimpleCompositeCandidateFlatTableProducer;

// Registriamo il modulo nel framework
DEFINE_FWK_MODULE(SimpleCompositeCandidateFlatTableProducer);