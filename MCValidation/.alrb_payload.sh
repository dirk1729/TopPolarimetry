        cd MCValidation/build
        asetup AnalysisBase,24.2.41
        cmake ../source
        make -j4
        source x86_64-*/setup.sh
        cd ../run
        MCVal_eljob.py --input-file /../../Derivation/L_ttbar/ --submission-dir L_ttbar
