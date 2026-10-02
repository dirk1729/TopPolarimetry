
IFS=/ 
var=($PWD)
dir=${var[-1]}
parent=${var[-2]}

if [ "${parent}/${dir}" != 'MCValidation/run' ]
then
  echo "You are running in the wrong directory. Please go to MCValidation/run and source run.sh"
else
  for s in L R; do
    rm -rf submitDir
    MCVal_eljob.py --input-file /../../Derivation/${s}_ttbar/ --submission-dir ${s}_ttbar
  done
fi

