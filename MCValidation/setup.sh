
if [ ! -d "build" ] 
then
    mkdir build
fi

if [ ! -d "run" ] 
then
    mkdir run
fi

if [ ! -f "run/run.sh" ]
then
    cp no_run.sh run/run.sh
fi

setupATLAS
cd build
asetup AnalysisBase,24.2.41

if [ ! -d "CMakeFiles" ]
then
    echo "First setup detected. Be sure to run compile.sh next!"
else
    source x86_64-*/setup.sh
fi

cd ..

