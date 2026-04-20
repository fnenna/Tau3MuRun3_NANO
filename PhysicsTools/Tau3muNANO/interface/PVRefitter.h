#ifndef PhysicsTools_Tau3muNANO_PVRefitter_h
#define PhysicsTools_Tau3muNANO_PVRefitter_h

#include "DataFormats/VertexReco/interface/Vertex.h"
#include "DataFormats/VertexReco/interface/VertexFwd.h"
#include "TrackingTools/TransientTrack/interface/TransientTrack.h"
#include "RecoVertex/KalmanVertexFit/interface/KalmanVertexFitter.h"
#include "RecoVertex/VertexPrimitives/interface/TransientVertex.h"

#include <vector>

class PVRefitter {
public:
    // Il costruttore può essere vuoto o inizializzare il fitter
    PVRefitter() : fitter_(true) {} 

    std::pair<reco::Vertex, int> refit(const std::vector<reco::TransientTrack>& svTracks, 
                                      const reco::Vertex& primaryVertex,
                                      const std::vector<reco::TransientTrack>& pvTracks) const;

private:
    KalmanVertexFitter fitter_;

    // Funzione interna per rimuovere le tracce del SV da quelle del PV
    std::vector<reco::TransientTrack> removeTracks(
        const std::vector<reco::TransientTrack>& pvTracks,
        const std::vector<reco::TransientTrack>& svTracks) const;
};

#endif