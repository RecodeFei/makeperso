#!/bin/bash

#-------------------------------------------------------------------------------
#
#    this file is used to check whether all the custpack apk which should be signed
#    has been added to file int/misc/releasekey.sh ,if not 
#    add to the right list in file releasekey.sh:ApkforSharedKey,ApkforMediaKey,ApkforPlatformKey
#    excluding *-res.apk which just containing resources,
#    if defined LOCAL_CERTIFICATE := shared in Android.mk,  MD5 in apk file: MD5: 5D:C8:20:1F:7D:B1:BA:4B:9C:8F:C4:41:46:C5:BC:C2
#    if defined LOCAL_CERTIFICATE := platform in Android.mk,MD5 in apk file: MD5: 8D:DB:34:2F:2D:A5:40:84:02:D7:56:8A:F2:1E:29:F9
#    if defined LOCAL_CERTIFICATE := media in Android.mk,   MD5 in apk file: MD5: 19:00:BB:FB:A7:56:ED:D3:41:90:22:57:6F:38:14:FF
#    if no LOCAL_CERTIFICATE defined in Android.mk,         MD5 in apk file: MD5: E8:9B:15:8E:4B:CF:98:8E:BD:09:EB:83:F5:37:8E:87

#    
#    HISTORY
#    2013/06/06 : Ding Erlei : creation
#-------------------------------------------------------------------------------
#

android_path=`pwd`
echo $android_path
#app_custpack="/local/alto5_wimdata_ng_gene/out/target/product/$1/system/custpack/"
app_custpack=$1
TOP=$2
echo "app_custpack:$app_custpack"
cd $app_custpack
find . -name *.apk | grep -v "JRD_custres" | while read apkname_path
do
#check APK zipalign
$TOP/out/host/linux-x86/bin/zipalign -c 4 $apkname_path
if [ "$?" == "1" ];then
    aligned_file=$TOP/`basename $apkname_path`
    $TOP/out/host/linux-x86/bin/zipalign -f 4 $apkname_path $aligned_file
    mv $aligned_file $apkname_path
fi
if (unzip -l $apkname_path |grep META-INF);then
    rsa_cmd=$(echo "unzip -p $apkname_path META-INF/*.*SA | keytool -printcert | grep MD5")
    rsa_md5=$(eval $rsa_cmd)
    echo $apkname_path
    apkname_path=${apkname_path#./}
    echo $rsa_md5
    #apkname=$(basename "$apkname_path" ".apk")
    if ( echo $rsa_md5 | grep "MD5: 5D:C8:20:1F:7D:B1:BA:4B:9C:8F:C4:41:46:C5:BC:C2" ) || ( echo $rsa_md5 | grep "MD5: E8:9B:15:8E:4B:CF:98:8E:BD:09:EB:83:F5:37:8E:87" ); then
        echo "$apkname_path need signed with shared key, please add to ApkforSharedKey list in file releasekey.sh"
        apkexist_cmd=$(echo "grep \"^${apkname_path}\" $android_path/releasekey.sh")
        eval $apkexist_cmd
        if [ $? -eq 0 ] ;then
           echo "$apkname_path has been added to file $android_path/releasekey.sh"
        else         
           add_cmd=$(echo "sed -i -e '/^shared_apkfiles=(/ a\\${apkname_path}' $android_path/releasekey.sh")
           eval $add_cmd
        fi           
    elif ( echo $rsa_md5 | grep "MD5: 8D:DB:34:2F:2D:A5:40:84:02:D7:56:8A:F2:1E:29:F9" ); then
        echo "$apkname need signed with platform key, please add to ApkforPlatformKey  list in file releasekey.sh"
        apkexist_cmd=$(echo "grep \"^$apkname_path\" $android_path/releasekey.sh")
        eval $apkexist_cmd
        if [ $? -eq 0 ] ;then
           echo "$apkname has been added to file $android_path/releasekey.sh"
        else         
           add_cmd=$(echo "sed -i -e '/^platform_apkfiles=(/ a\\$apkname_path' $android_path/releasekey.sh")
           eval $add_cmd
        fi

    elif ( echo $rsa_md5 | grep "MD5: 19:00:BB:FB:A7:56:ED:D3:41:90:22:57:6F:38:14:FF" ); then 
        echo "$apkname need signed with media key, please add to ApkforMediaKey  list in file releasekey.sh" 
        apkexist_cmd=$(echo "grep \"^$apkname_path\" $android_path/releasekey.sh")
        eval $apkexist_cmd
        if [ $? -eq 0 ] ;then
           echo "$apkname has been added to file $android_path/releasekey.sh"
        else         
           add_cmd=$(echo "sed -i -e '/^media_apkfiles=(/ a\\$apkname_path' $android_path/releasekey.sh")
           eval $add_cmd
        fi 
    else 
        echo "no need to sign again"
    fi
else
    echo "this apk has no rsa information"
fi

done
