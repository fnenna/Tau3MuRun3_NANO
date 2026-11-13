import os
import sys
import awkward as ak
import dask
import dask_awkward as dak
import hist
import uproot
import vector

vector.register_awkward()

# Redirect standard error (stderr) to a file
sys.stderr = open('errors.txt', 'w')

# Seed L1 di HLT_DoubleMu3_TkMu_DsTau3Mu_v, HLT_DoubleMu3_Trk_Tau3mu_v e HLT_DoubleMu4_3_LowMass_v
# (menu 2024), devono coincidere con L1_path_list in Tau3muNANO/python/Tau3mu_builder_cff.py
L1_SEEDS = [
    "L1_DoubleMu0er1p4_SQ_OS_dR_Max1p4",
    "L1_DoubleMu4er2p0_SQ_OS_dR_Max1p6",
    "L1_DoubleMu4p5_SQ_OS_dR_Max1p2",
    "L1_DoubleMu0er1p5_SQ_OS_dR_Max1p4",
    "L1_DoubleMu4_SQ_OS_dR_Max1p2",
    "L1_DoubleMu3er2p0_SQ_OS_dR_Max1p6",
    "L1_DoubleMu0er2p0_SQ_OS_dEta_Max1p5",
    "L1_DoubleMu0er2p0_SQ_OS_dEta_Max1p6",
    "L1_DoubleMu0er1p4_SQ_OS_dEta_Max1p2",
    "L1_DoubleMu0er1p5_SQ_OS_dEta_Max1p2",
    "L1_DoubleMu0er1p4_OQ_OS_dEta_Max1p6",
    "L1_DoubleMu5_SQ_OS_dR_Max1p6",
    "L1_TripleMu_3SQ_2p5SQ_0_OS_Mass_Max12",
    "L1_TripleMu_4SQ_2p5SQ_0_OS_Mass_Max12",
    "L1_TripleMu_5SQ_3SQ_0_DoubleMu_5_3_SQ_OS_Mass_Max9",
    "L1_TripleMu_5SQ_3SQ_0OQ_DoubleMu_5_3_SQ_OS_Mass_Max9",
    "L1_TripleMu_2SQ_1p5SQ_0OQ_Mass_Max12",
    "L1_TripleMu_3SQ_2p5SQ_0OQ_Mass_Max12",
]
# Seed con prescale 1 in tutte le colonne 2024 (brilcalc, run 380115-386924)
L1_UNPRESCALED_LOWMASS = [
    "L1_DoubleMu0er1p4_SQ_OS_dR_Max1p4",
    "L1_DoubleMu4er2p0_SQ_OS_dR_Max1p6",
    "L1_DoubleMu4p5_SQ_OS_dR_Max1p2",
]
# path tau3mu (TkMu / Trk): in piu' i due TripleMu sempre a PS 1
L1_UNPRESCALED_TAU3MU = L1_UNPRESCALED_LOWMASS + [
    "L1_TripleMu_4SQ_2p5SQ_0_OS_Mass_Max12",
    "L1_TripleMu_5SQ_3SQ_0_DoubleMu_5_3_SQ_OS_Mass_Max9",
]

# Funzione helper interna per rendere il codice leggibile
def dak_max3(a, b, c):
    return dak.where(a > b, 
                     dak.where(a > c, a, c), 
                     dak.where(b > c, b, c))

def DimuonMass(sub_df, first=1, second=2):
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

    # Sum of quadrivectors
    dimuon = mu1 + mu2
    invariant_mass = dimuon.mass
    
    # Apply the charge mask (OS = Opposite Sign)
    return dak.where(sub_df[f"DiMu{first}{second}_charge"] != 0, 0, invariant_mass)


def process_tau3mu_events(sub_df, isMC):
    # (rimossa la preselezione HLT_adaptation: aveva un bug di precedenza == / | ed era
    #  ridondante con il taglio HLT qui sotto, come in dsPhiPi_analyser.py)
    sub_df["isMC"] = isMC
    cutflow_lazy = {}
    # CUT 0 : Before cuts - skip event if no good triplets
    AnyTriplets = (sub_df.nTau3Mu >= 0)
    cutflow_lazy["BeforeCuts"] = dak.sum(AnyTriplets)
    # Save the number of events that have good triplets
    GoodTriplets = (sub_df.nTau3Mu >= 1)
    sub_df = sub_df[GoodTriplets]
    # CUT 1 : Check L1 and HLT decision
    # Check L1trigger: nessun taglio L1 (come in dsPhiPi_analyser.py), si salvano i singoli bit
    '''
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
    L1_passed = (sub_df[L1_triggers[0]]==1)
    for i in range(1, len(L1_triggers)):
        L1_passed = L1_passed | (sub_df[L1_triggers[i]]==1)
    dak_L1mask = L1_passed
    dak_L1Tpassed = dak.sum(dak_L1mask) 
    cutflow_lazy["L1Tpassed"] = dak_L1Tpassed # Count the survivors
    '''
    # From now on I only take into account the events that have at least one of the required L1 passed.
    L1seed = (1*sub_df["Trigger_L1_DoubleMu0er1p5_SQ_OS_dR_Max1p4"]
            + 10*sub_df["Trigger_L1_DoubleMu4_SQ_OS_dR_Max1p2"]
            + 100*sub_df["Trigger_L1_DoubleMu0er2p0_SQ_OS_dEta_Max1p6"]
            + 1000*ak.values_astype(sub_df["Trigger_L1_TripleMu_2SQ_1p5SQ_0OQ_Mass_Max12"], "int64"))
    sub_df["L1seed"] = L1seed

    # Singoli bit L1 (dopo prescale) e, se presenti, *_initial (prima dei prescale).
    # I seed assenti nel ntuple di input (produzioni vecchie) vengono saltati.
    input_fields = set(dak.fields(sub_df))
    L1_bits_saved = [f"Trigger_{s}{suf}" for s in L1_SEEDS for suf in ("", "_initial")
                     if f"Trigger_{s}{suf}" in input_fields]
    # OR dei seed mai prescalati nel 2024: L1_unprescaled (LowMass) e L1_unprescaled_tau3mu (path tau3mu)
    for label, seeds in (("L1_unprescaled", L1_UNPRESCALED_LOWMASS), ("L1_unprescaled_tau3mu", L1_UNPRESCALED_TAU3MU)):
        for suf in ("", "_initial"):
            names = [f"Trigger_{s}{suf}" for s in seeds]
            if all(n in input_fields for n in names):
                unpresc = sub_df[names[0]] == 1
                for n in names[1:]:
                    unpresc = unpresc | (sub_df[n] == 1)
                sub_df[f"{label}{suf}"] = dak.values_astype(unpresc, "int64")
                L1_bits_saved.append(f"{label}{suf}")

    # Check HLT
    # Path comune a segnale e controllo (Ds->phi pi): HLT_DoubleMu4_3_LowMass
    HLT_passed = (sub_df["Trigger_HLT_DoubleMu4_3_LowMass_v"]==1)
    dak_HLTmask = HLT_passed
    dak_HLTpassed = dak.sum(dak_HLTmask)  
    cutflow_lazy["HLTpassed"] = dak_HLTpassed
    HLTpath = dak.values_astype(1*sub_df["Trigger_HLT_DoubleMu3_TkMu_DsTau3Mu_v"]
            + 10*sub_df["Trigger_HLT_DoubleMu4_3_LowMass_v"]
            + 100*sub_df["Trigger_HLT_DoubleMu4_LowMass_Displaced_v"]
            + 1000*sub_df["Trigger_HLT_DoubleMu3_Trk_Tau3mu"], "int64")
    sub_df["HLTpath"] = HLTpath
    sub_df = sub_df[dak_HLTmask]
    # --------------------------------------------------------------------------------
    # STEP 1: Associate each muon and track in the triplets with their corresponding objects in the Muon/Track branches
    # --------------------------------------------------------------------------------
    columns_old = dak.fields(sub_df)
    for mu_idx in range(3):
        for i in range(len(columns_old)):
            if "Muon" in columns_old[i] and columns_old[i]!="nMuon":
                sub_df[f"{columns_old[i]}_{mu_idx+1}"] = sub_df[f"{columns_old[i]}"][sub_df[f"Tau3Mu_mu{mu_idx+1}_idx"]]
    # --- Combined Quality Variables (CombinedQuality) ---
    scalar_fields = ['run', 'luminosityBlock', 'event', 'nMuon', 'nTrack', 'nTau3Mu', 'L1seed', 'HLTpath', 'isMC']
    scalar_fields += L1_bits_saved
    if isMC>0:
        scalar_fields += ["Pileup_nPU"]
    else:
        scalar_fields += ["nPVtx"]

    sub_df["max_Muon_combinedQuality_updatedSta"] = dak_max3(
        sub_df.Muon_cQ_uS_1, sub_df.Muon_cQ_uS_2, sub_df.Muon_cQ_uS_3
    )

    sub_df["max_Muon_combinedQuality_trkKink"] = dak_max3(
        sub_df.Muon_cQ_tK_1, sub_df.Muon_cQ_tK_2, sub_df.Muon_cQ_tK_3
    )
    
    sub_df["max_Muon_combinedQuality_glbKink"] = dak_max3(
        sub_df.Muon_cQ_gK_1, sub_df.Muon_cQ_gK_2, sub_df.Muon_cQ_gK_3
    )

    sub_df["max_Muon_combinedQuality_trkRelChi2"] = dak_max3(
        sub_df.Muon_cQ_tRChi2_1, sub_df.Muon_cQ_tRChi2_2, sub_df.Muon_cQ_tRChi2_3
    )

    sub_df["max_Muon_combinedQuality_staRelChi2"] = dak_max3(
        sub_df.Muon_cQ_sRChi2_1, sub_df.Muon_cQ_sRChi2_2, sub_df.Muon_cQ_sRChi2_3
    )

    sub_df["max_Muon_combinedQuality_chi2LocalPosition"] = dak_max3(
        sub_df.Muon_cQ_Chi2LP_1, sub_df.Muon_cQ_Chi2LP_2, sub_df.Muon_cQ_Chi2LP_3
    )

    sub_df["max_Muon_combinedQuality_chi2LocalMomentum"] = dak_max3(
        sub_df.Muon_cQ_Chi2LM_1, sub_df.Muon_cQ_Chi2LM_2, sub_df.Muon_cQ_Chi2LM_3
    )

    sub_df["max_Muon_combinedQuality_localDistance"] = dak_max3(
        sub_df.Muon_cQ_lD_1, sub_df.Muon_cQ_lD_2, sub_df.Muon_cQ_lD_3
    )

    sub_df["max_Muon_combinedQuality_globalDeltaEtaPhi"] = dak_max3(
        sub_df.Muon_cQ_gDEP_1, sub_df.Muon_cQ_gDEP_2, sub_df.Muon_cQ_gDEP_3
    )

    sub_df["max_Muon_combinedQuality_tightMatch"] = dak_max3(
        sub_df.Muon_cQ_tM_1, sub_df.Muon_cQ_tM_2, sub_df.Muon_cQ_tM_3
    )

    sub_df["max_Muon_combinedQuality_glbTrackProbability"] = dak_max3(
        sub_df.Muon_cQ_gTP_1, sub_df.Muon_cQ_gTP_2, sub_df.Muon_cQ_gTP_3
    )

    # --- Compatibilità e MVA ---

    sub_df["max_Muon_caloCompatibility"] = dak_max3(
        sub_df.Muon_caloComp_1, sub_df.Muon_caloComp_2, sub_df.Muon_caloComp_3
    )

    sub_df["max_Muon_segmentCompatibility"] = dak_max3(
        sub_df.Muon_segmComp_1, sub_df.Muon_segmComp_2, sub_df.Muon_segmComp_3
    )

    sub_df["max_Muon_softMvaValue"] = dak_max3(
        sub_df.Muon_softMva_1, sub_df.Muon_softMva_2, sub_df.Muon_softMva_3
    )
    
    # Compute dimuon charge sum
    sub_df["DiMu12_charge"] = sub_df["Muon_charge_1"] + sub_df["Muon_charge_2"]
    sub_df["DiMu13_charge"] = sub_df["Muon_charge_1"] + sub_df["Muon_charge_3"]
    sub_df["DiMu23_charge"] = sub_df["Muon_charge_2"] + sub_df["Muon_charge_3"]
    # utility branches 
    sub_df["DiMu12_Mass"] = DimuonMass(sub_df, 1, 2)
    sub_df["DiMu13_Mass"] = DimuonMass(sub_df, 1, 3)
    sub_df["DiMu23_Mass"] = DimuonMass(sub_df, 2, 3)

    mask1 = (sub_df.DiMu12_Mass > 0) & (sub_df.DiMu23_Mass > 0)
    dimu_OS1_case1 = ak.where(sub_df.Tau3Mu_dr12 < sub_df.Tau3Mu_dr23, sub_df.DiMu12_Mass, sub_df.DiMu23_Mass)
    dimu_OS2_case1 = ak.where(sub_df.Tau3Mu_dr12 < sub_df.Tau3Mu_dr23, sub_df.DiMu23_Mass, sub_df.DiMu12_Mass)

    mask2 = (sub_df.DiMu12_Mass > 0) & (sub_df.DiMu13_Mass > 0)
    dimu_OS1_case2 = ak.where(sub_df.Tau3Mu_dr12 < sub_df.Tau3Mu_dr13, sub_df.DiMu12_Mass, sub_df.DiMu13_Mass)
    dimu_OS2_case2 = ak.where(sub_df.Tau3Mu_dr12 < sub_df.Tau3Mu_dr13, sub_df.DiMu13_Mass, sub_df.DiMu12_Mass)

    mask3 = (sub_df.DiMu13_Mass > 0) & (sub_df.DiMu23_Mass > 0)
    dimu_OS1_case3 = ak.where(sub_df.Tau3Mu_dr13 < sub_df.Tau3Mu_dr23, sub_df.DiMu13_Mass, sub_df.DiMu23_Mass)
    dimu_OS2_case3 = ak.where(sub_df.Tau3Mu_dr13 < sub_df.Tau3Mu_dr23, sub_df.DiMu23_Mass, sub_df.DiMu13_Mass)

    dimu_OS1 = ak.where(mask1, dimu_OS1_case1, 
                ak.where(mask2, dimu_OS1_case2, 
                    ak.where(mask3, dimu_OS1_case3, 0)))

    dimu_OS2 = ak.where(mask1, dimu_OS2_case1, 
                ak.where(mask2, dimu_OS2_case2, 
                    ak.where(mask3, dimu_OS2_case3, 0)))

    sub_df["DiMu_OS1"] = dimu_OS1
    sub_df["DiMu_OS2"] = dimu_OS2
    # --------------------------------------------------------------------------------
    # STEP 2: Physics Cuts
    # --------------------------------------------------------------------------------
    
    # Acceptance cuts (Endcap + Track)
    muon1_acceptance_barrel = ((abs(sub_df.Muon_eta_1) <= 1.2) & (sub_df.Muon_pt_1 > 3.5))
    muon2_acceptance_barrel = ((abs(sub_df.Muon_eta_2) <= 1.2) & (sub_df.Muon_pt_2 > 3.5))
    muon3_acceptance_barrel = ((abs(sub_df.Muon_eta_3) <= 1.2) & (sub_df.Muon_pt_3 > 3.5))
    muon1_acceptance_endcap = (((abs(sub_df.Muon_eta_1) > 1.2) & (abs(sub_df.Muon_eta_1) < 2.4)) & (sub_df.Muon_pt_1 > 2.0))
    muon2_acceptance_endcap = (((abs(sub_df.Muon_eta_2) > 1.2) & (abs(sub_df.Muon_eta_2) < 2.4)) & (sub_df.Muon_pt_2 > 2.0))
    muon3_acceptance_endcap = (((abs(sub_df.Muon_eta_3) > 1.2) & (abs(sub_df.Muon_eta_3) < 2.4)) & (sub_df.Muon_pt_3 > 2.0))

    muon_acceptance = (
        (muon1_acceptance_barrel | muon1_acceptance_endcap) &
        (muon2_acceptance_barrel | muon2_acceptance_endcap) &
        (muon3_acceptance_barrel | muon3_acceptance_endcap)
    )

    acceptance = muon_acceptance

    # Muon ID requirements
    muon_id = (
        (sub_df.Muon_isGlobal_1 == 1) &
        (sub_df.Muon_isGlobal_2 == 1) &
        (sub_df.Muon_isGlobal_3 == 1) &
        (sub_df.Muon_isMedium_1 == 1) &
        (sub_df.Muon_isMedium_2 == 1) &
        (sub_df.Muon_isMedium_3 == 1)
    )


    # Combine all base cuts
    base_cuts = acceptance & muon_id #& pv_sv_significance_cut
    dak_base_cuts = dak.sum(dak.any(base_cuts, axis=1)) 
    selected_fields = [
        col for col in dak.fields(sub_df)
        if (col not in columns_old) or (
            ("Tau3Mu" in col) and (col != "nTau3Mu") and ("HLT" not in col)
        )
    ] 

    dR_good = (sub_df.Tau3Mu_dr12<0.6)&(sub_df.Tau3Mu_dr13<0.6)&(sub_df.Tau3Mu_dr23<0.6)
    dZ_good = (sub_df.Tau3Mu_dz12<2.5)&(sub_df.Tau3Mu_dz13<2.5)&(sub_df.Tau3Mu_dz23<2.5)
    # Vertex significance cut
    pv_sv_significance_cut = (sub_df.Tau3Mu_flightDistBSSig >= 3.5)  # BS-SV, come dsPhiPi e analyzer 2022-2023

    dr_dz_sign = (dR_good&dZ_good&pv_sv_significance_cut)
    tri_muon_mass_cut = ((sub_df.Tau3Mu_mass >= 1.62) & (sub_df.Tau3Mu_mass <= 2.))

    # Trigger matching solo agli oggetti di HLT_DoubleMu4_3_LowMass (path dimuonico): richiesto
    # su mu1 e mu2 (i due muoni piu' duri, collezione ordinata in pT), come nell'analyzer 2022-2023
    triggerMatch_1 = ((sub_df.Muon_HLT_DoubleMu4_3_LowMass_v_1 > 0)
                    & (abs(sub_df.Muon_trgDR_1) < 0.03) & (abs(sub_df.Muon_trgDPT_1) < 0.1))
    triggerMatch_2 = ((sub_df.Muon_HLT_DoubleMu4_3_LowMass_v_2 > 0)
                    & (abs(sub_df.Muon_trgDR_2) < 0.03) & (abs(sub_df.Muon_trgDPT_2) < 0.1))

    cutflow_lazy["BaseCut"] = dak_base_cuts
    dak_dR_dZ_sign = dak.sum(dak.any(base_cuts&dr_dz_sign, axis=1)) 
    cutflow_lazy["dRdZ_significance"] = dak_dR_dZ_sign
    dak_tri_mass = dak.sum(dak.any(base_cuts&dr_dz_sign&tri_muon_mass_cut, axis=1))  
    cutflow_lazy["TriMuonMassCut"] = dak_tri_mass
    dak_trigger_match1 = dak.sum(dak.any(base_cuts&dr_dz_sign&tri_muon_mass_cut&triggerMatch_1, axis=1))
    cutflow_lazy["TriggerMatch1"] = dak_trigger_match1  
    dak_trigger_match2 = dak.sum(dak.any(base_cuts&dr_dz_sign&tri_muon_mass_cut&triggerMatch_1&triggerMatch_2, axis=1))  
    cutflow_lazy["TriggerMatch12"] = dak_trigger_match2
    cutflow_lazy["TriggerMatch123"] = dak_trigger_match2  # terzo muone non richiesto (path dimuonico)
    
    for col in selected_fields:
        sub_df[col] = sub_df[col][base_cuts&dr_dz_sign&tri_muon_mass_cut&triggerMatch_1&triggerMatch_2]
    
    sub_df = sub_df[dak.num(sub_df.Tau3Mu_mass, axis=1) > 0]
    sorted_idx = dak.argsort(sub_df["Tau3Mu_chi2"])
    # I select only one triplet, the lowest chi2 one
    for col in selected_fields:
        sub_df[col] = sub_df[col][sorted_idx][:, 0]
    
    sub_df = sub_df[selected_fields+scalar_fields]

    return sub_df, cutflow_lazy

def Analysis_Tau3Mu(tree, dataset_name, output_path, era, isMC):
    # Detect whether input is data or MC
    if not isMC:
        isMC = 0
    else:
        if "Ds" in dataset_name:
            isMC=1
        elif "Bp" in dataset_name:
            isMC=2
        elif "B0" in dataset_name:
            isMC=3
        elif "Run4" in dataset_name:
            isMC=4
        else:
            isMC = 5  # Could be a flag used downstream in processing logic

    # 1. Main logic execution
    arrays, selection_cutflow_dict = process_tau3mu_events(tree, isMC=isMC)

    # 2. Preparation of write jobs
    jobs = []
    for i in range(arrays.npartitions):
        # Add .root for safety
        destination = os.path.join(output_path, f"ntuple_{i}")
        job = uproot.dask_write(arrays.partitions[i], destination=destination, compute=False)
        jobs.append(job)
    
    # 3. Extraction of keys and lazy values
    cutflow_labels = list(selection_cutflow_dict.keys())
    cut_values_lazy = [selection_cutflow_dict[label] for label in cutflow_labels]

    # 4. SINGLE COMPUTE (Writing + Counts)
    from dask.distributed import performance_report

    # ... inside the main function, where you do the compute ...
    with performance_report(filename=f"dask-report-{era}.html"):
        all_results = dask.compute(*jobs, *cut_values_lazy)
    
    # 5. Recovery of calculated counts
    # We take only the last N elements, where N is the number of cuts
    computed_cutflow = all_results[-len(cutflow_labels):]

    # --- SAVING ---
    
    # Initialize the histogram with the real labels extracted from the dictionary
    h = hist.Hist(
        hist.axis.StrCategory(cutflow_labels, name="cut"),
        storage=hist.storage.Double()
    )

    # Filling (ensure they are float/int and not dask objects)
    h[:] = [float(x) for x in computed_cutflow]

    # Saving with Uproot
    cutflow_path = os.path.join(output_path, "cutflow.root")
    with uproot.recreate(cutflow_path) as f:
        f["cutflow"] = h