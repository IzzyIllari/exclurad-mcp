# EXCLURAD Bibliography

Compiled 2026-07-04. Citation data from INSPIRE-HEP (record 593271 for the original EXCLURAD paper, 62 citing records as of this date), arXiv, and GitHub.

---

## 1. Code and Methodology Papers

### 1.1 EXCLURAD

1. **QED radiative corrections in processes of exclusive pion electroproduction**
   A. Afanasev, I. Akushevich, V. Burkert, K. Joo
   Phys. Rev. D **66**, 074004 (2002); arXiv:hep-ph/0208183
   The original EXCLURAD paper. Covariant calculation of lowest-order QED radiative corrections to the five-fold differential cross section and beam-spin asymmetry of exclusive pion electroproduction, with exact phase-space integration (no peaking approximation) and covariant cancellation of the infrared divergence. Structure functions taken from MAID and SAID/AO model inputs. INSPIRE recid 593271.

2. **Amplitude-Based Analysis of QED Radiative Corrections to Electroproduction of η-Mesons on Protons**
   Isabella Illari, Andrei Afanasev, William J. Briscoe, Victor L. Kashevarov, Axel Schmidt, Igor I. Strakovsky
   arXiv:2604.22943 (submitted April 24, 2026; 30 pages, 28 figures, includes supplemental material; to be submitted to Phys. Rev. D)
   The 2026 update: extends EXCLURAD from the pion channel to exclusive η electroproduction using EtaMAID-2023 multipole amplitudes, at CLAS12 kinematics (E_beam = 6.535 GeV, Q² = 0.3–4.0 GeV², W = 1.49–2.0 GeV, full angular coverage).
   *Abstract (verbatim):* "A formalism for radiative correction calculations in exclusive η electroproduction on the proton is presented, extending the treatment developed for the pion channel. The EXCLURAD code is used in the radiative correction procedure with EtaMAID-2023 multipole amplitudes. The cross-section correction factor δ varies by up to ∼30% across the resonance region W = 1.49–2.0 GeV at E_beam = 6.535 GeV, with a local maximum near W ≃ 1.66 GeV driven by the S₁₁(1535) and S₁₁(1650) resonances. The beam-spin asymmetry is suppressed by 15–25% at the same kinematics. Numerical results covering Q² = 0.3–4.0 GeV² and the full angular range are provided for kinematics relevant to CLAS12 experiments at Jefferson Lab."

### 1.2 Related radiative-corrections methodology by Afanasev / Akushevich and collaborators

3. **Radiative effects in the processes of hadron electroproduction**
   I. V. Akushevich, N. M. Shumeiko, A. Soroko
   Eur. Phys. J. C **10**, 681–687 (1999); arXiv:hep-ph/9903325
   Basis of the HAPRAD code: lowest-order QED radiative corrections to the unpolarized semi-inclusive hadron electroproduction cross section.

4. **Lowest order QED radiative corrections to five-fold differential cross section of hadron leptoproduction** (HAPRAD 2.0)
   I. Akushevich, A. Ilyichev, M. Osipenko
   Phys. Lett. B **672**, 35–44 (2009); arXiv:0711.4789
   HAPRAD 2.0: semi-inclusive radiative corrections including the radiative tail from exclusive hadron production; complements EXCLURAD on the semi-inclusive side.

5. **POLRAD 2.0: FORTRAN code for the radiative corrections calculation to deep inelastic scattering of polarized particles**
   I. Akushevich, A. Ilyichev, N. Shumeiko, A. Soroko, A. Tolkachev
   Comput. Phys. Commun. **104**, 201 (1997); arXiv:hep-ph/9706516
   Predecessor code framework for polarized inclusive DIS radiative corrections; the covariant Bardin-Shumeiko approach it implements underlies EXCLURAD's treatment.

6. **ELRADGEN: Monte Carlo generator for radiative events in elastic electron-proton scattering**
   A. V. Afanasev, I. Akushevich, A. Ilyichev, B. Niczyporuk
   Czech. J. Phys. **53**, B449–B454 (2003); arXiv:hep-ph/0308106
   Companion Monte Carlo generator for radiative events in the elastic channel, same covariant methodology family.

7. **Two-photon exchange in exclusive pion electroproduction**
   A. Afanasev, A. Aleksejevs, S. Barkanova
   Phys. Rev. D **88**, 053008 (2013); arXiv:1207.1767
   Extends the exclusive-pion radiative-correction program beyond first order to two-photon exchange effects.

8. **CFNS Ad-Hoc meeting on Radiative Corrections Whitepaper**
   A. Afanasev et al.
   arXiv:2012.09970 (2020)
   Community whitepaper surveying the status of radiative corrections for lepton-hadron scattering, including exclusive processes and EXCLURAD.

9. **Exact and leading order radiative effects in semi-inclusive deep inelastic scattering**
   I. Akushevich et al.
   Phys. Rev. D **109**, 076028 (2024); arXiv:2403.18029
   Recent development of exact lowest-order radiative effects for SIDIS in the same theoretical framework.

**Section 1 count: 9 papers** (2 EXCLURAD + 7 related methodology).

---

## 2. Papers That Use EXCLURAD

Experimental analyses (drawn from the 62 INSPIRE-HEP records citing Phys. Rev. D 66, 074004) that applied EXCLURAD for radiative corrections. Listed newest first.

1. **Measurement of the hard exclusive π⁰ muoproduction cross section at COMPASS**
   G. D. Alexeev et al. (COMPASS Collaboration) — Phys. Lett. B **870**, 139832 (2025); arXiv:2412.19923
   EXCLURAD-based radiative corrections applied to the exclusive π⁰ muoproduction cross section.

2. **First measurement of hard exclusive π⁻Δ⁺⁺ electroproduction beam-spin asymmetries off the proton**
   S. Diehl et al. (CLAS Collaboration) — Phys. Rev. Lett. **131**, 021901 (2023); arXiv:2303.11762
   EXCLURAD used to estimate radiative effects on the beam-spin asymmetry in an exclusive channel.

3. **A multidimensional study of the structure function ratio σ_LT′/σ₀ from hard exclusive π⁺ electroproduction off protons in the GPD regime**
   S. Diehl et al. (CLAS Collaboration) — Phys. Lett. B **839**, 137761 (2023); arXiv:2210.14557
   EXCLURAD applied for radiative corrections to exclusive π⁺ beam-spin asymmetry observables.

4. **Measurement of the cross section for hard exclusive π⁰ muoproduction on the proton**
   M. G. Alexeev et al. (COMPASS Collaboration) — Phys. Lett. B **805**, 135454 (2020); arXiv:1903.12030
   Radiative corrections to exclusive π⁰ muoproduction evaluated using the EXCLURAD framework.

5. **Exclusive π⁰p electroproduction off protons in the resonance region at photon virtualities 0.4 ≤ Q² ≤ 1 GeV²**
   N. Markov et al. (CLAS Collaboration) — Phys. Rev. C **101**, 015208 (2020); arXiv:1907.11974
   EXCLURAD used for radiative corrections to resonance-region π⁰ cross sections.

6. **Exclusive π⁰ Electroproduction in the Resonance Region**
   N. Markov et al. — Few Body Syst. **59**, 134 (2018)
   Companion resonance-region π⁰ analysis using EXCLURAD radiative corrections.

7. **Hard exclusive pion electroproduction at backward angles with CLAS**
   K. Park et al. (CLAS Collaboration) — Phys. Lett. B **780**, 340–345 (2018); arXiv:1711.08486
   EXCLURAD radiative corrections applied to backward-angle exclusive pion cross sections.

8. **Exclusive η electroproduction at W > 2 GeV with CLAS and transversity generalized parton distributions**
   I. Bedlinskiy et al. (CLAS Collaboration) — Phys. Rev. C **95**, 035202 (2017); arXiv:1703.06982
   EXCLURAD-based radiative corrections for the exclusive η channel (a direct precursor use-case for the 2026 η update).

9. **Rosenbluth separation of the π⁰ electroproduction cross section off the neutron**
   M. Mazouz et al. (Jefferson Lab Hall A Collaboration) — Phys. Rev. Lett. **118**, 222002 (2017); arXiv:1702.00835
   Exclusive π⁰ radiative corrections informed by the EXCLURAD approach in the Rosenbluth separation.

10. **Measurement of target and double-spin asymmetries for the e p → e π⁺(n) reaction in the nucleon resonance region at low Q²**
    X. Zheng et al. (CLAS Collaboration) — Phys. Rev. C **94**, 045206 (2016); arXiv:1607.03924
    EXCLURAD used to correct spin-asymmetry observables for radiative effects.

11. **Measurements of e p → e′π⁺n at W = 1.6–2.0 GeV and extraction of nucleon resonance electrocouplings at CLAS**
    K. Park et al. (CLAS Collaboration) — Phys. Rev. C **91**, 045203 (2015); arXiv:1412.0274
    EXCLURAD radiative corrections in the π⁺ electrocoupling extraction.

12. **Exclusive π⁰ electroproduction at W > 2 GeV with CLAS**
    I. Bedlinskiy et al. (CLAS Collaboration) — Phys. Rev. C **90**, 025205 (2014); arXiv:1405.0988
    EXCLURAD applied to deeply exclusive π⁰ cross sections.

13. **Separated structure functions for exclusive K⁺Λ and K⁺Σ⁰ electroproduction at 5.5 GeV with CLAS**
    D. S. Carman et al. (CLAS Collaboration) — Phys. Rev. C **87**, 025204 (2013); arXiv:1212.1336
    EXCLURAD methodology adapted for radiative corrections to exclusive kaon channels.

14. **Near threshold neutral pion electroproduction at high momentum transfers and generalized form factors**
    P. Khetarpal et al. (CLAS Collaboration) — Phys. Rev. C **87**, 045205 (2013); arXiv:1211.6460
    EXCLURAD radiative corrections for near-threshold π⁰ production.

15. **Deep exclusive π⁺ electroproduction off the proton at CLAS**
    K. Park et al. (CLAS Collaboration) — Eur. Phys. J. A **49**, 16 (2013); arXiv:1206.2326
    EXCLURAD used for exclusive π⁺ cross-section radiative corrections.

16. **Measurement of exclusive π⁰ electroproduction structure functions and their relationship to transversity GPDs**
    I. Bedlinskiy et al. (CLAS Collaboration) — Phys. Rev. Lett. **109**, 112001 (2012); arXiv:1206.6355
    EXCLURAD radiative corrections to π⁰ structure-function separation.

17. **Measurement of the generalized form factors near threshold via γ*p → nπ⁺ at high Q²**
    K. Park et al. (CLAS Collaboration) — Phys. Rev. C **85**, 035208 (2012); arXiv:1201.0903
    EXCLURAD applied near the pion-production threshold at high Q².

18. **Measurement of the partial cross sections σ_TT, σ_LT, and σ_T + εσ_L of the p(e,e′π⁺)n reaction in the Δ(1232) resonance**
    J. M. Kirkpatrick et al. — Phys. Rev. C **84**, 028201 (2011); arXiv:0810.4563
    EXCLURAD radiative corrections in the Δ-region π⁺ partial cross-section separation.

19. **Neutral pion electroproduction in the resonance region at high Q²**
    A. N. Villano et al. — Phys. Rev. C **80**, 035203 (2009); arXiv:0906.2839
    EXCLURAD used for radiative corrections to high-Q² π⁰ resonance-region cross sections.

20. **Electroproduction of pπ⁺π⁻ off protons at 0.2 < Q² < 0.6 GeV² and 1.3 < W < 1.57 GeV with CLAS**
    G. V. Fedotov et al. (CLAS Collaboration) — Phys. Rev. C **79**, 015204 (2009); arXiv:0809.1562
    EXCLURAD-informed radiative corrections for the two-pion channel.

21. **Transverse momentum dependence of semi-inclusive pion production**
    H. Mkrtchyan et al. — Phys. Lett. B **665**, 20–25 (2008); arXiv:0709.3020
    EXCLURAD used to assess the exclusive radiative tail in a Hall C semi-inclusive pion analysis.

22. **Electroproduction of φ(1020) mesons at 1.4 ≤ Q² ≤ 3.8 GeV² measured with the CLAS spectrometer**
    J. P. Santoro et al. (CLAS Collaboration) — Phys. Rev. C **78**, 025210 (2008); arXiv:0803.3537
    EXCLURAD methodology applied to radiative corrections in exclusive φ production.

23. **Polarized structure function σ_LT′ for p(e→,e′K⁺)Λ in the nucleon resonance region**
    R. Nasseripour et al. (CLAS Collaboration) — Phys. Rev. C **77**, 065208 (2008); arXiv:0801.4711
    EXCLURAD-based corrections for the polarized kaon electroproduction observable.

24. **Cross sections and beam asymmetries for e→p → enπ⁺ in the nucleon resonance region for 1.7 ≤ Q² ≤ 4.5 GeV²**
    K. Park et al. (CLAS Collaboration) — Phys. Rev. C **77**, 015208 (2008); arXiv:0709.1946
    EXCLURAD radiative corrections to π⁺ cross sections and beam asymmetries.

25. **Separated structure functions for the exclusive electroproduction of K⁺Λ and K⁺Σ⁰ final states**
    P. Ambrozewicz et al. (CLAS Collaboration) — Phys. Rev. C **75**, 045203 (2007); arXiv:hep-ex/0611036
    EXCLURAD approach used for kaon-channel radiative corrections.

26. **Recoil polarization measurements for neutral pion electroproduction at Q² = 1 (GeV/c)²**
    J. J. Kelly et al. — Phys. Rev. C **75**, 025201 (2007); arXiv:nucl-ex/0509004
    EXCLURAD radiative corrections in Hall A recoil-polarization π⁰ analysis.

27. **Measurement of the N → Δ(1232) transition at high momentum transfer by π⁰ electroproduction**
    M. Ungaro et al. (CLAS Collaboration) — Phys. Rev. Lett. **97**, 112003 (2006); arXiv:hep-ex/0606042
    EXCLURAD used to correct π⁰ cross sections in the N→Δ transition extraction.

28. **Single π⁺ electroproduction on the proton in the first and second resonance regions at 0.25 < Q² < 0.65 GeV²**
    H. Egiyan et al. (CLAS Collaboration) — Phys. Rev. C **73**, 025204 (2006); arXiv:nucl-ex/0601007
    EXCLURAD radiative corrections to resonance-region π⁺ cross sections.

29. **Electron scattering from high-momentum neutrons in deuterium**
    A. V. Klimenko et al. (CLAS Collaboration) — Phys. Rev. C **73**, 035212 (2006); arXiv:nucl-ex/0510032
    EXCLURAD framework referenced/applied for exclusive-channel radiative effects.

30. **Measurement of the polarized structure function σ_LT′ for pion electroproduction in the Roper-resonance region**
    K. Joo et al. (CLAS Collaboration) — Phys. Rev. C **72**, 058202 (2005); arXiv:nucl-ex/0504027
    EXCLURAD corrections applied to σ_LT′.

31. **Measurement of the polarized structure function σ_LT′ for p(e→,e′π⁺)n in the Δ(1232) resonance region**
    K. Joo et al. (CLAS Collaboration) — Phys. Rev. C **70**, 042201 (2004); arXiv:nucl-ex/0407013
    EXCLURAD radiative corrections to the polarized π⁺ observable.

32. **Measurement of beam-spin asymmetries for π⁺ electroproduction above the baryon resonance region**
    H. Avakian et al. (CLAS Collaboration) — Phys. Rev. D **69**, 112004 (2004); arXiv:hep-ex/0301005
    EXCLURAD used to evaluate radiative effects on beam-spin asymmetries.

33. **Measurement of the polarized structure function σ_LT′ for p(e→,e′p)π⁰ in the Δ(1232) resonance region**
    K. Joo et al. (CLAS Collaboration) — Phys. Rev. C **68**, 032201 (2003); arXiv:nucl-ex/0301012
    One of the first published uses of EXCLURAD for exclusive π⁰ radiative corrections.

### Theses and proceedings that used EXCLURAD

34. H. S. Ko, *Neutral Pion Electroproduction and development of a Neutral Particle Spectrometer*, PhD thesis (2020).
35. M. Gorzellik, *Cross-section measurement of exclusive π⁰ muoproduction and firmware design for an FPGA-based detector readout*, PhD thesis, Freiburg (2018) — COMPASS.
36. A. Kim, *Single and double spin asymmetries for deeply virtual exclusive π⁰ production on longitudinally polarized proton target with CLAS*, PhD thesis (2014).
37. K. Chirapatpimol, *Precision measurement of electroproduction of π⁰ near threshold*, PhD thesis, University of Virginia (2012).
38. M. Ungaro et al., *Exclusive π⁰, η electroproduction in the resonance region at high Q²*, AIP Conf. Proc. **1374**, 357–361 (2011).
39. V. Kubarovsky, *Deeply virtual exclusive reactions with CLAS*, Nucl. Phys. B Proc. Suppl. **219–220**, 118–125 (2011).
40. P. Khetarpal, *Near threshold neutral pion electroproduction at high momentum transfers*, PhD thesis.
41. K. Joo, *Single π⁰ electroproduction in the resonance region with CLAS*, Chin. Phys. C **33**, 1254–1256 (2009).
42. J. P. Santoro, *Electroproduction of φ(1020) mesons at high Q²*, PhD thesis, Virginia Tech.
43. J. D. Lachniet, *A high precision measurement of the neutron magnetic form factor using the CLAS detector*, PhD thesis, Carnegie Mellon.
44. (Old Dominion U. thesis) *Deep Virtual Pion Pair Production* (2023).
45. (Charles U. thesis) *Proton structure studies using hard exclusive processes at COMPASS experiment* (2024).
46. M. Ghaffar, *Higher order radiative corrections in lepton-proton scattering using covariant approach*, PhD thesis, Memorial University of Newfoundland (2025).

*Note:* The remaining INSPIRE citers are theory/review works that cite EXCLURAD without applying it to data, e.g. M. Boër et al., arXiv:2512.15064 (3D hadron imaging review); A. Aleksejevs et al., Phys. Rev. D 113, 113002 (2026), arXiv:2507.22097; T. Liu et al., JHEP 11, 157 (2021), arXiv:2108.13371 and Phys. Rev. D 104, 094033 (2021), arXiv:2008.02895 (QED/QCD factorization approach to SIDIS RCs); *Precision studies of QCD in the low-energy domain of the EIC*, Prog. Part. Nucl. Phys. 131, 104032 (2023), arXiv:2211.15746; G. I. Smirnov, arXiv:hep-ph/0504045; A. Ilyichev et al., Phys. Rev. D 72, 033018 (2005), arXiv:hep-ph/0504191; A. Aleksejevs et al., Nucl. Phys. B Proc. Suppl. 245, 17 (2013), arXiv:1309.3313.

**Section 2 count: 33 journal-published experimental analyses + 13 theses/proceedings (46 total application-type entries), out of 62 total INSPIRE citers.**

---

## 3. Context Resources

### MAID / etaMAID model references (sources of EXCLURAD's structure-function lookup tables)

1. **A unitary isobar model for pion photo- and electroproduction on the proton up to 1 GeV** (MAID98)
   D. Drechsel, O. Hanstein, S. S. Kamalov, L. Tiator
   Nucl. Phys. A **645**, 145–174 (1999); arXiv:nucl-th/9807001
   The original MAID unitary isobar model; MAID98 tables are among EXCLURAD's standard pion-channel inputs.

2. **MAID2000** — updated version of the unitary isobar model of Ref. 1, distributed via the Mainz MAID web interface (https://maid.kph.uni-mainz.de/); used as an alternative pion-channel input table in EXCLURAD.

3. **Unitary isobar model — MAID2007**
   D. Drechsel, S. S. Kamalov, L. Tiator
   Eur. Phys. J. A **34**, 69–97 (2007); arXiv:0710.0306
   The 2007 MAID update covering all channels of pion photo- and electroproduction up to W = 2 GeV.

4. **An isobar model for η photo- and electroproduction on the nucleon** (etaMAID)
   W.-T. Chiang, S. N. Yang, L. Tiator, D. Drechsel
   Nucl. Phys. A **700**, 429–453 (2002); arXiv:nucl-th/0110034
   The original etaMAID isobar model: Breit-Wigner s-channel resonances, Born terms, and t-channel vector-meson exchange.

5. **Eta and etaprime photoproduction on the nucleon with the isobar model EtaMAID2018**
   L. Tiator, M. Gorchtein, V. L. Kashevarov, et al.
   Eur. Phys. J. A **54**, 210 (2018); arXiv:1807.04525
   Major EtaMAID update (photoproduction of η and η′ on protons and neutrons).

6. **EtaMAID-2023** — updated electroproduction multipole amplitudes (M_l±, E_l±, S_l± for l = 0–5) by the Mainz MAID group (V. L. Kashevarov, L. Tiator, et al.). Not yet a standalone journal publication; the lookup tables are described and used in arXiv:2604.22943, and distributed via the MAID portal (https://maid.kph.uni-mainz.de/).

### Code repository

7. **JeffersonLab/exclurad** — https://github.com/JeffersonLab/exclurad
   Official EXCLURAD repository (Fortran, ~94% of codebase). README describes radiative corrections to exclusive pion electroproduction using covariant infrared-divergence cancellation and exact phase-space integration, MAID and AO model inputs, and notes extensibility to other exclusive channels (kaon production, deuteron breakup). Cites Phys. Rev. D 66, 074004 (2002).

**Section 3 count: 6 model references + 1 code repository.**

---

### Key INSPIRE / arXiv identifiers for quick lookup
- Original paper: INSPIRE recid **593271**, arXiv:hep-ph/0208183, doi:10.1103/PhysRevD.66.074004
- 2026 update: arXiv:2604.22943
- Citing-papers API query: `https://inspirehep.net/api/literature?q=refersto%3Arecid%3A593271`
