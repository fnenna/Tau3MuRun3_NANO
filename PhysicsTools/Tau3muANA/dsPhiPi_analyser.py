import math
import pandas as pd
import uproot
import os
import numpy as np
import awkward as ak
import dask_awkward as dak
import hist
import dask
import vector
vector.register_awkward()
import sys

def increase_bits(func):
    def wrap(array, *args, **kwargs):
        # Converte l'input in int64 prima di passarlo alla funzione (es. dak.sum)
        array_64 = ak.values_astype(array, "int64")
        return func(array_64, *args, **kwargs)
    return wrap

# 2. "Decoriamo" la funzione originale
# Creiamo una versione potenziata di dak.sum
safe_sum = increase_bits(dak.sum)

# Redirige lo standard error (stderr) su un file
sys.stderr = open('errori_sistema.txt', 'w')

# Funzione helper interna per rendere il codice leggibile
def dak_max3(a, b, c):
    return dak.where(a > b, 
                     dak.where(a > c, a, c), 
                     dak.where(b > c, b, c))

def DimuonMass(sub_df, first=1,second =2):
    # "lazy" quadrivectors
    mu1 = ak.zip({
        "pt": sub_df[f"Muon_pt_{first}"], 
        "eta": sub_df[f"Muon_eta_{first}"], 
        "phi": sub_df[f"Muon_phi_{first}"], 
        "energy": sub_df[f"Muon_energy_{first}"]
    }, with_name="Momentum4D")

    mu2 = ak.zip({
        "pt": sub_df[f"Muon_pt_{second}"], 
        "eta": sub_df[f"Muon_eta_{second}"], 
        "phi": sub_df[f"Muon_phi_{second}"], 
        "energy": sub_df[f"Muon_energy_{second}"]
    }, with_name="Momentum4D")

    # quadrivectors sum
    dimuon = mu1 + mu2
    invariant_mass = dimuon.mass
    
    # Applichiamo la maschera per la carica (OS = Opposite Sign)
    return dak.where(sub_df[f"DiMu{first}{second}_charge"] != 0, 0, invariant_mass)


def process_tau3mu_events(sub_df, isMC):
    cutflow_lazy = {}
    #CUT 0 : Before cuts - skip event if no good triplets
    AnyTriplets = (sub_df.nTau2MuTrk >= 0)
    #dak_BeforeCuts = dak.sum(dak.any(AnyTriplets,axis=1)) 
    cutflow_lazy["BeforeCuts"] = dak.sum(AnyTriplets)
    #save the number of events that have good triplets
    GoodTriplets = (sub_df.nTau2MuTrk >= 1)
    #dak_GoodTriplets = dak.sum(dak.any(GoodTriplets,axis=1)) 
    sub_df = sub_df[GoodTriplets]
    # CUT 1 : Check L1 and HLT decision
    # Check L1trigger
    L1_triggers = ["Trigger_L1_DoubleMu0er1p5_SQ_OS_dR_Max1p4",
                   "Trigger_L1_DoubleMu0er1p4_SQ_OS_dR_Max1p4",
                   "Trigger_L1_DoubleMu4_SQ_OS_dR_Max1p2",
                   "Trigger_L1_DoubleMu4p5_SQ_OS_dR_Max1p2",
                   "Trigger_L1_TripleMu_5SQ_3SQ_0OQ_DoubleMu_5_3_SQ_OS_Mass_Max9",
                   "Trigger_L1_TripleMu_5SQ_3SQ_0_DoubleMu_5_3_SQ_OS_Mass_Max9",
                   "Trigger_L1_DoubleMu0er2p0_SQ_OS_dEta_Max1p6",
                   "Trigger_L1_DoubleMu0er2p0_SQ_OS_dEta_Max1p5",
                   "Trigger_L1_TripleMu_2SQ_1p5SQ_0OQ_Mass_Max12",
                   "Trigger_L1_TripleMu_3SQ_2p5SQ_0OQ_Mass_Max12",        
    ]
    #dak.any because we need only one of the 
    #L1_passed = (dak.any(((dak.str.match_substring(sub_df.Trigger_l1name,L1_triggers[0]))|(dak.str.match_substring(sub_df.Trigger_l1name,L1_triggers[1]))|(dak.str.match_substring(sub_df.Trigger_l1name,L1_triggers[2]))|(dak.str.match_substring(sub_df.Trigger_l1name,L1_triggers[3]))|(dak.str.match_substring(sub_df.Trigger_l1name,L1_triggers[4]))|(dak.str.match_substring(sub_df.Trigger_l1name,L1_triggers[5])))&((sub_df.Trigger_l1Finaldecision) == 1), axis =1)) #keepdims = True
    #L1_passed = ((dak.str.match_substring(sub_df.Trigger_l1name,L1_triggers[0]))|(dak.str.match_substring(sub_df.Trigger_l1name,L1_triggers[1]))|(dak.str.match_substring(sub_df.Trigger_l1name,L1_triggers[2]))|(dak.str.match_substring(sub_df.Trigger_l1name,L1_triggers[3]))|(dak.str.match_substring(sub_df.Trigger_l1name,L1_triggers[4]))|(dak.str.match_substring(sub_df.Trigger_l1name,L1_triggers[5]))|(dak.str.match_substring(sub_df.Trigger_l1name,L1_triggers[6]))|(dak.str.match_substring(sub_df.Trigger_l1name,L1_triggers[7]))|(dak.str.match_substring(sub_df.Trigger_l1name,L1_triggers[8]))|(dak.str.match_substring(sub_df.Trigger_l1name,L1_triggers[9])))&(sub_df.Trigger_l1Finaldecision == 1) #keepdims = True
    L1_passed = (sub_df[L1_triggers[0]]==1)
    for i in range(1, len(L1_triggers)):
        L1_passed = L1_passed | (sub_df[L1_triggers[i]]==1)
    dak_L1mask = L1_passed
    dak_L1Tpassed = dak.sum(dak_L1mask) 
    cutflow_lazy["L1Tpassed"] = dak_L1Tpassed # Conta i superstiti
    #From now on I ony take into account the events that have at least one of the required L1 passed.
    #L1seed = dak.zeros_like(sub_df.nTau3Mu, dtype=int)+ (1*dak.values_astype(dak.any(dak.str.match_substring(sub_df.Trigger_l1name,"L1_DoubleMu0er1p5_SQ_OS_dR_Max1p4") & (sub_df.Trigger_l1Finaldecision == 1), axis = 1), int)
    #        + 10*dak.values_astype(dak.any(dak.str.match_substring(sub_df.Trigger_l1name,"L1_DoubleMu4_SQ_OS_dR_Max1p2") & (sub_df.Trigger_l1Finaldecision == 1), axis = 1), int)
    #        + 1000*dak.values_astype(dak.any(dak.str.match_substring(sub_df.Trigger_l1name,"L1_DoubleMu0er2p0_SQ_OS_dEta_Max1p6") & (sub_df.Trigger_l1Finaldecision == 1), axis =1), int)
    #        + 10000*dak.values_astype(dak.any(dak.str.match_substring(sub_df.Trigger_l1name,"L1_TripleMu_2SQ_1p5SQ_0OQ_Mass_Max12") & (sub_df.Trigger_l1Finaldecision == 1), axis =1), int))
    L1seed = (1*sub_df["Trigger_L1_DoubleMu0er1p5_SQ_OS_dR_Max1p4"]
            + 10*sub_df["Trigger_L1_DoubleMu4_SQ_OS_dR_Max1p2"]
            + 100*sub_df["Trigger_L1_DoubleMu0er2p0_SQ_OS_dEta_Max1p6"]
            + 1000*ak.values_astype(sub_df["Trigger_L1_TripleMu_2SQ_1p5SQ_0OQ_Mass_Max12"], "int64"))
    sub_df["L1seed"] = L1seed
    # Check HLT
    #HLT_passed = dak.any(dak.str.match_substring(sub_df.Trigger_hltname,"HLT_DoubleMu3_Trk_Tau3mu_v") & (sub_df.Trigger_hltdecision == 1), axis = 1)
    HLT_passed = (sub_df["Trigger_HLT_DoubleMu3_TkMu_DsTau3Mu_v"]==1)
    dak_HLTmask = HLT_passed
    dak_HLTpassed = dak.sum(dak_HLTmask&dak_L1mask)  
    cutflow_lazy["HLTpassed"] = dak_HLTpassed
    HLTpath = dak.values_astype(1*sub_df["Trigger_HLT_DoubleMu3_TkMu_DsTau3Mu_v"]
            + 10*sub_df["Trigger_HLT_DoubleMu4_3_LowMass_v"]
            + 100*sub_df["Trigger_HLT_DoubleMu4_LowMass_Displaced_v"], "int64")
    sub_df["HLTpath"] = HLTpath
    sub_df = sub_df[dak_L1mask&dak_HLTmask]
    # --------------------------------------------------------------------------------
    # STEP 1: Associate each muon and track in the triplets with their corresponding objects in the Muon/Track branches
    # --------------------------------------------------------------------------------
    columns_old = dak.fields(sub_df)
    #pairs_mu01_index, pairs_tri_mu01_index, pairs_mu02_index, pairs_tri_mu02_index, pairs_mu03_index, pairs_tri_mu03_index = threeMuonsFinder(sub_df)
    for mu_idx in range(2):
        for i in range(len(columns_old)):
            if "Muon" in columns_old[i] and columns_old[i]!="nMuon":
                sub_df[f"{columns_old[i]}_{mu_idx+1}"] = sub_df[f"{columns_old[i]}"][sub_df[f"Tau2MuTrk_mu{mu_idx+1}_idx"]]
    for i in range(len(columns_old)):
        if "Track_" in columns_old[i] and columns_old[i]!="nTrack":
            sub_df[f"{columns_old[i]}_tr"] = sub_df[f"{columns_old[i]}"][sub_df[f"Tau2MuTrk_tr_idx"]]
    # --- Variabili di Qualità Combinata (CombinedQuality) ---

    sub_df["max_Muon_combinedQuality_updatedSta"] = dak.where(
        sub_df.Muon_cQ_uS_1 > sub_df.Muon_cQ_uS_2, sub_df.Muon_cQ_uS_1, sub_df.Muon_cQ_uS_2
    )

    sub_df["max_Muon_combinedQuality_trkKink"] = dak.where(
        sub_df.Muon_cQ_tK_1 > sub_df.Muon_cQ_tK_2, sub_df.Muon_cQ_tK_1,sub_df.Muon_cQ_tK_2,
    )
    
    sub_df["max_Muon_combinedQuality_glbKink"] = dak.where(
        sub_df.Muon_cQ_gK_1 > sub_df.Muon_cQ_gK_2, sub_df.Muon_cQ_gK_1, sub_df.Muon_cQ_gK_2,
    )

    sub_df["max_Muon_combinedQuality_trkRelChi2"] = dak.where(
        sub_df.Muon_cQ_tRChi2_1 > sub_df.Muon_cQ_tRChi2_2, sub_df.Muon_cQ_tRChi2_1, sub_df.Muon_cQ_tRChi2_2
    )

    sub_df["max_Muon_combinedQuality_staRelChi2"] = dak.where(
        sub_df.Muon_cQ_sRChi2_1 > sub_df.Muon_cQ_sRChi2_2, sub_df.Muon_cQ_sRChi2_1, sub_df.Muon_cQ_sRChi2_2,
    )

    sub_df["max_Muon_combinedQuality_chi2LocalPosition"] = dak.where(
        sub_df.Muon_cQ_Chi2LP_1 > sub_df.Muon_cQ_Chi2LP_2, sub_df.Muon_cQ_Chi2LP_1, sub_df.Muon_cQ_Chi2LP_2
    )

    sub_df["max_Muon_combinedQuality_chi2LocalMomentum"] = dak.where(
        sub_df.Muon_cQ_Chi2LM_1 > sub_df.Muon_cQ_Chi2LM_2, sub_df.Muon_cQ_Chi2LM_1, sub_df.Muon_cQ_Chi2LM_2
    )

    sub_df["max_Muon_combinedQuality_localDistance"] = dak.where(
        sub_df.Muon_cQ_lD_1 > sub_df.Muon_cQ_lD_2, sub_df.Muon_cQ_lD_1, sub_df.Muon_cQ_lD_2
    )

    sub_df["max_Muon_combinedQuality_globalDeltaEtaPhi"] = dak.where(
        sub_df.Muon_cQ_gDEP_1 > sub_df.Muon_cQ_gDEP_2, sub_df.Muon_cQ_gDEP_1, sub_df.Muon_cQ_gDEP_2
    )

    sub_df["max_Muon_combinedQuality_tightMatch"] = dak.where(
        sub_df.Muon_cQ_tM_1 > sub_df.Muon_cQ_tM_2, sub_df.Muon_cQ_tM_1, sub_df.Muon_cQ_tM_2
    )

    sub_df["max_Muon_combinedQuality_glbTrackProbability"] = dak.where(
        sub_df.Muon_cQ_gTP_1 > sub_df.Muon_cQ_gTP_2, sub_df.Muon_cQ_gTP_1, sub_df.Muon_cQ_gTP_2
    )

    # --- Compatibilità e MVA ---

    sub_df["max_Muon_caloCompatibility"] = dak.where(
        sub_df.Muon_caloComp_1 > sub_df.Muon_caloComp_2, sub_df.Muon_caloComp_1, sub_df.Muon_caloComp_2
    )

    sub_df["max_Muon_segmentCompatibility"] = dak.where(
        sub_df.Muon_segmComp_1 > sub_df.Muon_segmComp_2, sub_df.Muon_segmComp_1, sub_df.Muon_segmComp_2
    )

    sub_df["max_Muon_softMvaValue"] = dak.where(
        sub_df.Muon_softMva_1 > sub_df.Muon_softMva_2, sub_df.Muon_softMva_1, sub_df.Muon_softMva_2
    )
    
    # Compute dimuon charge sum
    sub_df["DiMu12_charge"] = sub_df["Muon_charge_1"] + sub_df["Muon_charge_2"]
    #utilities branches 
    sub_df["DiMu12_Mass"] = DimuonMass(sub_df, 1, 2)

    # --------------------------------------------------------------------------------
    # STEP 2: Physics Cuts
    # --------------------------------------------------------------------------------
    
    # Acceptance cuts (Endcap + Track)
    muon_acceptance = (
        (sub_df.Muon_pt_1 >= 2) &
        (sub_df.Muon_pt_2 >= 2) &
        (abs(sub_df.Muon_eta_1) <= 2.4) &
        (abs(sub_df.Muon_eta_2) <= 2.4)
    )

    track_acceptance = (
        (sub_df.Track_pt_tr >= 2) &
        (abs(sub_df.Track_eta_tr) <= 2.4)
    )

    acceptance = muon_acceptance & track_acceptance


    # Vertex significance cut
    pv_sv_significance_cut = (sub_df.Tau2MuTrk_flightDistSig >= 3.5)

    # Muon ID requirements
    muon_id = (
        (sub_df.Muon_isGlobal_1 == 1) &
        (sub_df.Muon_isGlobal_2 == 1) &
        (sub_df.Muon_isMedium_1 == 1) &
        (sub_df.Muon_isMedium_2 == 1)
    )

    # Track quality requirements
    track_quality = ((sub_df.Track_dz_tr < 20) & (sub_df.Track_dxy_tr < 0.3))

    # Combine all base cuts
    base_cuts = acceptance & muon_id & track_quality & pv_sv_significance_cut 
    dak_base_cuts = dak.sum(dak.any(base_cuts, axis=1)) 
    selected_fields = [
        col for col in dak.fields(sub_df)
        if (col not in columns_old) or (
            ("Tau2MuTrk" in col) and (col != "nTau2MuTrk") and ("HLT" not in col)
        )
    ] 

    tri_muon_mass_cut = ((sub_df.Tau2MuTrk_mass >= 1.62) & (sub_df.Tau2MuTrk_mass <= 2.1))
    phi_mass_window = ((sub_df.DiMu12_Mass >= 0.98) & (sub_df.DiMu12_Mass <= 1.06))


    triggerMatch_1 = ((sub_df.Muon_HLT_DoubleMu3_TkMu_DsTau3Mu_v_1 + sub_df.Muon_HLT_DoubleMu3_Trk_Tau3mu_1 + sub_df.Muon_HLT_DoubleMu3_Trk_Tau3mu_NoL1Mass_v_1 + sub_df.Muon_HLT_DoubleMu4_3_LowMass_v_1 + sub_df.Muon_HLT_DoubleMu4_LowMass_Displaced_v_1 > 0)
                    & (abs(sub_df.Muon_trgDR_1) < 0.03) & (abs(sub_df.Muon_trgDPT_1) < 0.1))
    triggerMatch_2 = ((sub_df.Muon_HLT_DoubleMu3_TkMu_DsTau3Mu_v_2 + sub_df.Muon_HLT_DoubleMu3_Trk_Tau3mu_2 + sub_df.Muon_HLT_DoubleMu3_Trk_Tau3mu_NoL1Mass_v_2 + sub_df.Muon_HLT_DoubleMu4_3_LowMass_v_2 + sub_df.Muon_HLT_DoubleMu4_LowMass_Displaced_v_2 > 0)
                    & (abs(sub_df.Muon_trgDR_2) < 0.03) & (abs(sub_df.Muon_trgDPT_2) < 0.1))


    cutflow_lazy["BaseCut"] = dak_base_cuts
    dak_phi_mass = dak.sum(dak.any(base_cuts&phi_mass_window, axis=1))  
    cutflow_lazy["PhiMassCut"] = dak_phi_mass
    dak_tri_mass = dak.sum(dak.any(base_cuts&phi_mass_window&tri_muon_mass_cut, axis=1))  
    cutflow_lazy["TriMuonMassCut"] = dak_tri_mass
    dak_trigger_match1 = dak.sum(dak.any(base_cuts&phi_mass_window&tri_muon_mass_cut&triggerMatch_1, axis=1))
    cutflow_lazy["TriggerMatch1"] = dak_trigger_match1  
    dak_trigger_match2 = dak.sum(dak.any(base_cuts&phi_mass_window&tri_muon_mass_cut&triggerMatch_1&triggerMatch_2, axis=1))  
    cutflow_lazy["TriggerMatch12"] = dak_trigger_match2
    cutflow_lazy["TriggerMatch123"] = dak_trigger_match2
    
    for col in selected_fields:
        print(selected_fields)
        sub_df[col] = sub_df[col][base_cuts&phi_mass_window&tri_muon_mass_cut&triggerMatch_1&triggerMatch_2]
    
    sorted = dak.argsort(sub_df["Tau2MuTrk_chi2"])
    for col in selected_fields:
        sub_df[col] = sub_df[col][sorted]
    
    sub_df = sub_df[selected_fields]

    #I select only one triplet, the lowest chi2 one
    sub_df = sub_df[dak.num(sub_df.Tau2MuTrk_mass, axis=1) > 0]

    sub_df = sub_df[:, 0]

    return sub_df, cutflow_lazy#, dak_BeforeCuts, dak_L1Tpassed, dak_HLTpassed, dak_base_cuts, dak_phi_mass, dak_tri_mass, dak_trigger_match1, dak_trigger_match2

def Analysis_DsPhiPi(tree, dataset_name, output_path, era, stream):
    '''
    # Detect whether input is data or MC
    if any(year in dataset_name for year in ["2022", "2023", "2024"]) and "MC" not in dataset_name:
        isMC = 0
    elif "MC" in dataset_name:
        if "Ds" in dataset_name:
            isMC=1
        if "Bp" in dataset_name:
            isMC=2
        if "B0" in dataset_name:
            isMC=3
        if "Run4" in dataset_name:
            isMC=4
        isMC = 5  # Could be a flag used downstream in processing logic
    '''
    isMC = 0

    # 1. Esecuzione logica principale
    arrays, selection_cutflow_dict = process_tau3mu_events(tree, isMC=isMC)

    # 2. Preparazione Job di scrittura
    print(f"Writing output to: {output_path}")
    jobs = []
    for i in range(arrays.npartitions):
        # Aggiungi .root per sicurezza
        destination = os.path.join(output_path, f"ntuple_{i}.root")
        job = uproot.dask_write(arrays.partitions[i], destination=destination, compute=False)
        jobs.append(job)
    
    # 3. Estrazione chiavi e valori lazy
    cutflow_labels = list(selection_cutflow_dict.keys())
    cut_values_lazy = [selection_cutflow_dict[label] for label in cutflow_labels]

    # 4. COMPUTE UNICO (Scrittura + Conteggi)
    print("Executing Dask computation (Writing + Cutflow)...")
    from dask.distributed import performance_report

    # ... dentro la funzione principale, dove fai il compute ...
    with performance_report(filename=f"dask-report-{era}.html"):
        #results = dask.compute(*jobs, *cut_values_lazy)
        all_results = dask.compute(*jobs, *cut_values_lazy)
    
    # 5. Recupero dei conteggi calcolati
    # Prendiamo solo gli ultimi N elementi, dove N è il numero di tagli
    computed_cutflow = all_results[-len(cutflow_labels):]

    # --- SALVATAGGIO ---
    print("Saving cutflow...")
    
    # Inizializza l'istogramma con le etichette reali estratte dal dizionario
    h = hist.Hist(
        hist.axis.StrCategory(cutflow_labels, name="cut"),
        storage=hist.storage.Double()
    )

    # Riempimento (assicurati che siano float/int e non oggetti dask)
    h[:] = [float(x) for x in computed_cutflow]

    # Salvataggio con Uproot
    cutflow_path = os.path.join(output_path, "cutflow.root")
    with uproot.recreate(cutflow_path) as f:
        f["cutflow"] = h
        print(f"Cutflow saved as TH1 to {cutflow_path}")
    
