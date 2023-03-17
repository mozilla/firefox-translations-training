#!/bin/bash
##
# Downloads Tatoeba Challenge data (train, devset and eval in same package)
#

set -x
set -euo pipefail

echo "###### Downloading Tatoeba-Challenge data"

src_three_letter=$1
trg_three_letter=$2
src=$3
trg=$4
output_prefix=$5
version=$6

tmp="$(dirname "${output_prefix}")/${version}"
mkdir -p "${tmp}"

archive_path="${tmp}/${version}-${src_three_letter}-${trg_three_letter}.tar"

#try both combinations of language codes 
if wget -O "${archive_path}" "https://object.pouta.csc.fi/${version}/${src_three_letter}-${trg_three_letter}.tar"; then
   package_src=${src}
   package_trg=${trg} 
elif wget -O "${archive_path}" "https://object.pouta.csc.fi/${version}/${trg_three_letter}-${src_three_letter}.tar"; then
   package_src=${trg}
   package_trg=${src}
fi

#extract all in same directory, saves the trouble of parsing directory structure
tar -xf "${archive_path}" --directory ${tmp} --strip-components 4 

mv ${tmp}/train.src.gz ${output_prefix}/corpus/tc_${version}.${package_src}.gz
mv ${tmp}/train.trg.gz ${output_prefix}/corpus/tc_${version}.${package_trg}.gz

cat ${tmp}/dev.src | gzip > ${output_prefix}/devset/tc_${version}.${package_src}.gz
cat ${tmp}/dev.trg | gzip > ${output_prefix}/devset/tc_${version}.${package_trg}.gz

cat ${tmp}/test.src | gzip > ${output_prefix}/eval/tc_${version}.${package_src}.gz
cat ${tmp}/test.trg | gzip > ${output_prefix}/eval/tc_${version}.${package_trg}.gz

rm -rf "${tmp}"


echo "###### Done: Downloading Tatoeba-Challenge data"
