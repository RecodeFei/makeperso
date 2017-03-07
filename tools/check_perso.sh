#!/bin/bash


usage() {
  echo "Usage: `readlink -f $0` -t TOP folder -p TARGET_PRODUCT"
  echo "Example: `readlink -f $0` -t . -p m823_orange"
  exit 1
}


read_property() {
    local build_prop=$JRD_OUT_SYSTEM/build.prop
    cat $build_prop | grep "$1=" | awk -F'=' '{print $2}'
}

put() {
    echo "<$*>" >> "results.xml"
}

put_head() {
    put "?$1?"
}

tag_start() {
    put $1
}

tag_end() {
    put '/'$1
}

tag_value() {
    put $*'/'
}

feature_tags() {
    local featurelist
    ls "$JRD_OUT_SYSTEM/etc/permissions" | grep ".xml" | while read -r line
    do
        featurelist=$(xmlstarlet sel -t -m "/permissions/feature" -v "@name" -o " " $JRD_OUT_SYSTEM/etc/permissions/$line)
        for item in $featurelist
        do
            tag_value "feature name=\"$item\""
        done
    done
}

apk_tags() {
    local apk_package
    local apk_name
    local apk_version

    find $JRD_OUT_SYSTEM -name "*.apk" | sort -V | while read -r line
    do
        apk_package=$(prebuilts/sdk/tools/linux/bin/aapt d permissions $line | grep "package:" | awk '{print $2}')
        apk_name=$(prebuilts/sdk/tools/linux/bin/aapt d badging $line | grep "application-label:" | awk -F"'" '{print $2}')
        apk_name=${apk_name//&/&amp;}
        if [ -z "$apk_name" ]; then
            apk_name=$(basename $line)
            apk_name=${apk_name//.apk/}
        fi
        apk_version=$(prebuilts/sdk/tools/linux/bin/aapt d badging $line | grep -o -E "versionName='[^\']*'" | awk -F"'" '{print $2}')
        tag_value "apk name=\"$apk_name\" package=\"$apk_package\" version=\"$apk_version\""
    done
}

read_sheet_csv() {
    local col_num
    local value
    col_num=$(cat $TOP/manifests/sheet/$TARGET_PRODUCT.csv | head -1 | awk -F, '{for (i=1;i<=NF;i++) if ($i == "'$1'") print i}')
    value=$(cat $TOP/manifests/sheet/$TARGET_PRODUCT.csv | grep "$Main" | awk -F, '{print $'$col_num'}')
    echo "$value"
}



while getopts t:p: o
do
    case "$o" in
    t) TOP="$OPTARG";;
    p) TARGET_PRODUCT="$OPTARG";;
    [?]) usage ;;
    esac
done

if [ -z "$TOP" ]; then
    echo "Please specify TOP folder."
    usage
else
    TOP=$(readlink -e $TOP)
fi
if [ -z "$TARGET_PRODUCT" ]; then
    echo "Please specify target product."
    usage
fi

PRODUCT_OUT=$TOP/out/target/product/$TARGET_PRODUCT
JRD_OUT_SYSTEM=$PRODUCT_OUT/system
PERSO_VERSION=`cat ${JRD_OUT_SYSTEM}/system.ver`
Author=`whoami`

# perso build date
BuildDate=$(date +"%F %T")
# product model
Model=$(read_property "ro.product.model")
# fingerprint
Fingerprint=$(read_property "ro.build.fingerprint")
# product abi
ABI=$(read_property "ro.product.cpu.abi")
# platform version
AndroidVersion=$(read_property "ro.build.version.release")
Platform=$(read_property "ro.board.platform")
vendor=$(echo ${Fingerprint} | cut -d'/' -f1)
if [ "${vendor}" == "CMCC" ]; then
    Main=${PERSO_VERSION:1:9}
    Perso=${PERSO_VERSION:10:2}
    PT_code='BG'
else
    Main=${PERSO_VERSION:1:3}${PERSO_VERSION:6:1}
    Perso=${PERSO_VERSION:4:2}${PERSO_VERSION:7:1}
    PT_code=${PERSO_VERSION:8:2}
fi

if [ -f "$TOP/manifests/sheet/$TARGET_PRODUCT.csv" ]; then
    Efuse=$(read_sheet_csv "EFUSE")
    if [ "$Efuse" == true ]; then
        Efuse=Y
    else
        Efuse=N
    fi
    Simlock=$(read_sheet_csv "SIMLOCK")
    if [ "$Simlock" == true ]; then
        Simlock=Y
    else
        Simlock=N
    fi
    Defconfig=$(read_sheet_csv "DEFCONFIG")
    Branch=$(read_sheet_csv "PRODUCTBRANCH")
else
    Efuse=""
    Simlock=""
    Defconfig=""
    Branch=""
fi

if [ -f "results.xml" ]; then
    rm results.xml
fi

put_head "xml version=\"1.0\" encoding=\"utf-8\""
tag_start "results"
tag_value "project name=\"$TARGET_PRODUCT\""
tag_value "main name=\"$Main\""
tag_value "perso name=\"$Perso\""
tag_value "platform name=\"$Platform\""
tag_value "platform_code name=\"$PT_code\""
tag_value "model name=\"$Model\""
tag_value "branch name=\"$Branch\""
tag_value "builddate name=\"$BuildDate\""
tag_value "fingerprint name=\"$Fingerprint\""
tag_value "abi name=\"$ABI\""
tag_value "author name=\"$Author\""
tag_value "androidver name=\"$AndroidVersion\""
tag_value "efuse name=\"$Efuse\""
tag_value "simlock name=\"$Simlock\""
tag_value "kernelconfig name=\"$Defconfig\""
tag_start "featurelist"
feature_tags
tag_end "featurelist"
tag_start "apklist"
apk_tags
tag_end "apklist"
tag_end "results"
