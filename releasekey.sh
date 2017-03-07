#!/bin/bash

if [ -z "$1" ]; then
	echo "Please give the key"
	exit 1
fi
if [ -z "$2" ]; then
	echo "Please give the platform name"
	exit 1
fi

product_path=`pwd`
echo $product_path

script_path=$(dirname $0)

processApk() {
	$script_path/signapk.py $1 $2 $3 $4

	$product_path/out/host/linux-x86/bin/zipalign -f 4 $product_path/out/target/product/$4/system/custpack/$1.signed $product_path/out/target/product/$4/system/custpack/$1.signed_aligned

	mv $product_path/out/target/product/$4/system/custpack/$1.signed_aligned $product_path/out/target/product/$4/system/custpack/$1
	
	rm $product_path/out/target/product/$4/system/custpack/$1.signed

}

platform_apkfiles=( 
)
shared_apkfiles=(
)
media_apkfiles=(
)

for apkfile in ${platform_apkfiles[*]}
do
if [ -f $product_path/out/target/product/$2/system/custpack/$apkfile ]; then
echo "signing $apkfile"
processApk $apkfile platform $1 $2
fi
done

for apkfile in ${shared_apkfiles[*]}
do
if [ -f $product_path/out/target/product/$2/system/custpack/$apkfile ]; then
echo "signing $apkfile"
processApk $apkfile shared $1 $2
fi
done

for apkfile in ${media_apkfiles[*]}
do
if [ -f $product_path/out/target/product/$2/system/custpack/$apkfile ]; then
echo "signing $apkfile"
processApk $apkfile media $1 $2
fi
done

sed -i "s/test-keys/release-keys/g" $product_path/out/target/product/$2/system/build.prop

#$product_path/out/host/linux-x86/bin/make_ext4fs -s -l 838860800 -a system $product_path/out/target/product/$2/system.img $product_path/out/target/product/$2/system
