#include "PhysicsTools/NanoAOD/interface/SimpleFlatTableProducer.h"
#include "DataFormats/PatCandidates/interface/PackedCandidate.h"
#include "FWCore/Framework/interface/MakerMacros.h"

typedef SimpleFlatTableProducer<pat::PackedCandidate> SimplePFCandidateFlatTableProducer;

// Registriamo il modulo nel framework
DEFINE_FWK_MODULE(SimplePFCandidateFlatTableProducer);