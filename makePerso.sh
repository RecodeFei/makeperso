#!/bin/bash
# Script to build perso image
#

export PS4="+ [\t] "
set -o errexit

usage() {
  echo "Usage: `readlink -f $0` -p TARGET_PRODUCT -t TOP folder -s ORIGIN_SYSTEM_IMAGE_PATH -y SYSTEM_SIZE -u ORIGIN_USERDATA_IMAGE_PATH -z USERDATA_SIZE -m TARGET_THEME -v PERSO_VERSION"
  echo "Example: `readlink -f $0` -p alto5 -t . -s system.img -y systemsize -u userdata.img -z userdatasize -m DNA -v Y3H1ZZ40BG00"
  exit 1
}

traperror () {
    local errcode=$?
    local lineno="$1"
    local funcstack="$2"
    local linecallfunc="$3"

    echo "ERROR: line ${lineno} - command exited with status: ${errcode}"
    if [ "${funcstack}" != "" ]; then
        echo -n "Error at function ${funcstack[0]}() "
        if [ "${linecallfunc}" != "" ]; then
            echo -n "called at line ${linecallfunc}"
        fi
        echo
    fi
}

# Get the exact value of a build variable.
function get_build_var()
{
    CALLED_FROM_SETUP=true BUILD_SYSTEM=build/core \
      command make --no-print-directory -f build/core/config.mk dumpvar-$1
}

function override_exist_folder {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    # $1 target file folder
    # $2 source file folder
    local target_folder=$1
    if [ ! -d "$target_folder" ] ; then
        mkdir -p $target_folder
    fi
    # Only copy files that already present at media folder before.
    for target_file in `ls $target_folder`
    do
        local source_file=$2/$target_file
        if [ ! -L "$target_folder/$target_file" ] && [ -f "$target_folder/$target_file" ] && [ -f "$source_file" ] ; then
            cp -f $source_file $target_folder
        fi
    done
    trap - ERR
}

function override_exist_file {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    # $1 target file
    # $2 source file
    local target_file=$1
    local source_file=$2
    if [ ! -L "$target_file" ] && [ -f "$target_file" ] && [ -f "$source_file" ] ; then
        cp -f $source_file $target_file
    fi
    trap - ERR
}

function prepare_translations {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    echo "now creating the strings.xml from the strings.xls"
    if [ ! -d "$JRD_CUSTOM_RES" ] ; then
        mkdir -p $JRD_CUSTOM_RES
    fi
    if [ -f "$JRD_BUILD_PATH_DEVICE/perso/string_res.ini" ] && [ -f "$JRD_WIMDATA/wlanguage/src/strings.xls" ] ; then
        $JRD_TOOLS_ARCT w -LM -I $JRD_BUILD_PATH_DEVICE/perso/string_res.ini -o $JRD_CUSTOM_RES $JRD_WIMDATA/wlanguage/src/strings.xls $TOP > /dev/null
    else
        echo "Can't find string.xls file."
    fi
    trap - ERR
}

function prepare_res_config {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    echo "now copy donottranslate-cldr.xml from res to $JRD_CUSTOM_RES"
    if [ ! -d "$JRD_CUSTOM_RES" ] ; then
        mkdir -p $JRD_CUSTOM_RES
    fi
	find $TOP/frameworks/base/core/res/res/ | grep "donottranslate-cldr.xml" | while read -r line
	do
		fnpath=$(echo $line | sed "s:$TOP::g")
		dirpath=$(dirname $fnpath)
		if [ -d $JRD_CUSTOM_RES/$dirpath ];then
			echo "cp -f $line $JRD_CUSTOM_RES/$fnpath"
			cp -f $line $JRD_CUSTOM_RES/$fnpath
		fi
	done
    trap - ERR
}

function prepare_timezone {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    echo "now copy timezone option files according to locale settings"
    local timezone_xml_path="packages/apps/Settings/res"
    for lang in $PRODUCT_LOCALES
    do
        main_lang=$(echo $lang | cut -d"_" -f1)
        if [ -d "$TOP/$timezone_xml_path/xml-$lang" ] ; then
            echo "cp -rf $TOP/$timezone_xml_path/xml-$lang $JRD_CUSTOM_RES/$timezone_xml_path/"
            cp -rf $TOP/$timezone_xml_path/xml-$lang $JRD_CUSTOM_RES/$timezone_xml_path/
        elif [ -d "$TOP/$timezone_xml_path/xml-$main_lang" ] ; then
            echo "cp -rf $TOP/$timezone_xml_path/xml-$main_lang $JRD_CUSTOM_RES/$timezone_xml_path/"
            cp -rf $TOP/$timezone_xml_path/xml-$main_lang $JRD_CUSTOM_RES/$timezone_xml_path/
        else
            echo "doing nothing..."
        fi
    done
    trap - ERR
}

function prepare_photos {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    echo "now building the customized icons..."
    if [ -f "$JRD_WIMDATA/wcustores/Photos/$TARGET_PRODUCT/images.zip" ] ; then
        unzip -o -q $JRD_WIMDATA/wcustores/Photos/$TARGET_PRODUCT/images.zip -d $JRD_CUSTOM_RES
    fi
    trap - ERR
}

function prepare_ringtone {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    echo "now building the customized audio..."
    local audio_folder=$JRD_OUT_SYSTEM/media/audio
    if [ ! -d "$audio_folder" ] ; then
        mkdir -p $audio_folder
    else
        clean_intermediates_folder $audio_folder
    fi
    mkdir -p $audio_folder/alarms
    mkdir -p $audio_folder/notifications
    mkdir -p $audio_folder/ringtones
    mkdir -p $audio_folder/switch_on_off
    mkdir -p $audio_folder/ui
    mkdir -p $audio_folder/cb_ring

    # PR#956108 - SH SWD4 Connectivity - ming.ren@jrdcom.com 66826 - 20150326 begin
    # [BUGFIX] [WiFi] Change sound for "new wifi"
    # [BUGFIX] MOD-BEGIN by TCTNB.ji.chen,2015/04/09,PR968111,idol3476 and idol3 both need wifi ring customization
    mkdir -p $audio_folder/wifi_ring
    # [BUGFIX] MOD-END by TCTNB.ji.chen
    # PR#956108 - SH SWD4 Connectivity - Ming.Ren - 20150326 end

    #delete the origin ringtone files firstly
    pushd $audio_folder > /dev/null
    if [ `find . -type f | xargs rm` ] ; then
        echo "Didn't find any audio files, go on ..."
    fi
    popd > /dev/null

    #unzip audio.zip to target path
    unzip -o -q $JRD_WIMDATA/wcustores/Audios/$TARGET_PRODUCT/audios.zip -d $JRD_CUSTOM_RES
    cp -r $JRD_CUSTOM_RES/frameworks/base/data/sounds/Alarm/*          $audio_folder/alarms
    cp -r $JRD_CUSTOM_RES/frameworks/base/data/sounds/Notification/*   $audio_folder/notifications
    cp -r $JRD_CUSTOM_RES/frameworks/base/data/sounds/Ringtones/*      $audio_folder/ringtones
    cp -r $JRD_CUSTOM_RES/frameworks/base/data/sounds/Switch_On_Off/*  $audio_folder/switch_on_off
    cp -r $JRD_CUSTOM_RES/frameworks/base/data/sounds/UI/*             $audio_folder/ui
    cp -r $JRD_CUSTOM_RES/frameworks/base/data/sounds/CB_Ring/*        $audio_folder/cb_ring
    # PR#956108 - SH SWD4 Connectivity - ming.ren@jrdcom.com 66826 - 20150326 begin
    # [BUGFIX] [WiFi] Change sound for "new wifi"
    # [BUGFIX] MOD-BEGIN by TCTNB.ji.chen,2015/04/09,PR968111,idol3-5.5 also need wifi ring customization
    cp ./frameworks/base/data/sounds/wifi_notification.ogg             $audio_folder/wifi_ring/
    # [BUGFIX] MOD-END by TCTNB.ji.chen
    # PR#956108 - SH SWD4 Connectivity - Ming.Ren - 20150326 end
    trap - ERR
}

function prepare_fonts {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    echo "now building the customized fonts..."
    #TODO: customize fonts

    trap - ERR
}

function check_if_3rd_apk_has_lib {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR

    local apk=$1
    local apkdir=${apk%%.apk}

    mkdir -p $apkdir

    if [ ! `unzip -o -d $apkdir $apk lib/* > /dev/null` ] ; then
        if [ ! -d "$apkdir/lib" ] ; then
            echo "$apk has no jni library to process."
            rm -rf $apkdir
        else
            pushd $apkdir/lib > /dev/null
            if [ -d "arm64-v8a" ] ; then
                mv arm64-v8a arm64
                rm -rf `ls | grep -v -e "^arm64$"`
            elif [ -d "armeabi-v7a" ] ; then
                mv armeabi-v7a arm
                rm -rf `ls | grep -v -e "^arm$"`
            elif [ -d "armeabi" ] ; then
                mv armeabi arm
                rm -rf `ls | grep -v -e "^arm$"`
            else
                echo "The apk didn't contain valid abi for arm device. exiting now ..."
                popd > /dev/null
                exit 1
            fi
            popd > /dev/null
            zip -d $apk 'lib/*.so'
            zipalign -f 4 $apk $apkdir/$apk
            rm -f $apk
        fi
    fi

    trap - ERR
}

function prepare_3rd_party_apk {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR

    local apk_path
    local apk_cmd
    local check_path

    set -x

    #remove all apk in /system/custpack/app
    #clean_intermediates_folder $JRD_OUT_CUSTPACK/app

    #parse command from jrd_build_apps.mk and run command one by one
    cat $JRD_BUILD_PATH_DEVICE/perso/buildres/jrd_build_apps.mk | sed -e 's/#.*//g' | while read -r line
    do
        if ( echo $line | grep -q "mkdir" ) ; then
            apk_path=$(echo $line | awk '{print "mkdir -p "$4}' | sed -e 's/(//g' -e 's/)//g')
            if [ -n "$apk_path" ] ; then
                if [ `eval $apk_path` ] ; then
                    echo "Cannot mkdir $apk_path, continue ..."
                fi
            fi
        elif ( echo $line | grep -q "cp" ) ; then
            apk_cmd=$(echo $line | awk '{print $2 " " $3 " " $4}' | sed -e 's/(//g' -e 's/)//g')
            if [ `eval $apk_cmd` ] ; then
                echo "Didn't find corresponding files, continue ..."
            fi
        fi
    done

    if [ -f "$TOP/extra_apk.lst" ] ; then
        customize_standalone_apk
        rm -f $TOP/extra_apk.lst
    fi

    check_path=$(find $JRD_OUT_CUSTPACK/app -name "*.apk" | grep -v "/removeable" | while read -r line; do echo $(dirname $line); done | sort | uniq)

    for path in ${check_path[@]}
    do
        pushd $path > /dev/null
        ls | grep -E "*.apk" | while read -r line
        do
            check_if_3rd_apk_has_lib $line
        done
        popd > /dev/null
    done

    set +x

    trap - ERR
}

function customize_standalone_apk {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR

    local standalone_apk_path
    local standalone_apk_package
    local origin_apk_path
    local origin_apk_name
    local extra_apk_name
    local extra_apk_path
    local extra_apk_package
    local num=$(wc -l $TOP/extra_apk.lst | awk '{print $1}')
    local index=0
    local readline

    pushd $TOP > /dev/null

    find vendor/tctalone/TctAppPackage -name "*.apk" | while read -r line
    do
        if [ $index -eq $num ] ; then
            break
        fi
        standalone_apk_path=$(dirname $line)

        cat $TOP/extra_apk.lst | while read -r readline
        do
            extra_apk_name=$(basename $readline)
            if ( echo $readline | grep "PrivAPK" ) ; then
                extra_apk_path=$JRD_OUT_CUSTPACK/app/priv-app/$extra_apk_name
            elif ( echo $readline | grep "ExtraAPK" ) ; then
                extra_apk_path=$JRD_OUT_CUSTPACK/app/unremoveable/$extra_apk_name
            elif ( echo $readline | grep "ExtraAPKremoveable" ) ; then
                extra_apk_path=$JRD_OUT_CUSTPACK/app/removeable/$extra_apk_name
            else
                continue
            fi
            if [ -f "$extra_apk_path" ] ; then
                standalone_apk_package=$($MY_AAPT_TOOL d --values permissions $line  | head -1 | awk '{print $2}')
                extra_apk_package=$($MY_AAPT_TOOL d --values permissions $extra_apk_path | head -1 | awk '{print $2}')
                if [ "$standalone_apk_package" == "$extra_apk_package" ] ; then
                    origin_apk_path=$(get_custo_apk_path $standalone_apk_path)
                    origin_apk_name=$(get_local_package_name $standalone_apk_path)
                    if [ -d "$origin_apk_path/$origin_apk_name" ] ; then
                        rm -rf $origin_apk_path/$origin_apk_name
                    elif [ -f "$origin_apk_path/${origin_apk_name}.apk" ] ; then
                        rm -f $origin_apk_path/${origin_apk_name}.apk
                    fi
                    let "index = $index + 1"
                    break
                fi
            fi
        done
    done
    popd > /dev/null

    trap - ERR
}

function prepare_media {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    #$(hide) cp $(JRD_WIMDATA)/wcustores/Media/$(TARGET_PRODUCT)/* $(PRODUCT_OUT)/system/media
    echo "now copy boot/shutdown animation.gif..."
    cp -rf $JRD_WIMDATA/wcustores/Media/$TARGET_PRODUCT/* $PRODUCT_OUT/system/media
    trap - ERR
}

function prepare_plfs {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    echo "now process plf to xml..."
    local $PLF_FILES

    PLF_PARSE_TOOL=$TOP/device/tct/common/perso/tools/prd2xml

    set -x

    pushd $TOP > /dev/null

    for folder in ${MY_PLF_FILE_FOLDER[@]}
    do
        if [ -d "$folder" ] ; then
            PLF_FILES=($(find $folder -type f -name *.plf))
        fi
        for plf in ${PLF_FILES[@]}
        do
            PLF_TARGET_XML_FOLDER=$JRD_CUSTOM_RES/$(dirname $plf)/res/values
            mkdir -p $PLF_TARGET_XML_FOLDER
            LD_LIBRARY_PATH=$PLF_PARSE_TOOL $PLF_PARSE_TOOL/prd2h --def $PLF_PARSE_TOOL/prd2h_def.xml --dest $PLF_TARGET_XML_FOLDER $TOP/$plf
            ret=$?
            if [ $ret -ne 0 -a $ret -ne 139 ] ; then # ignore error #139
                echo "Parse PLF files error, exiting now ... "
                exit
            else
                rm -rf $PLF_TARGET_XML_FOLDER/isdm_*.h
                rm -rf $PLF_TARGET_XML_FOLDER/isdm_*.log
            fi
        done
    done

    popd > /dev/null

    set +x

    trap - ERR
}

function prepare_launcher_workspace {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    # copy launcher workspace to out $JRD_CUSTOM_RES folder
    # TODO: the path of workspace.xml file are different for some projects which not use the standalone launcher
    local workspace=vendor/tctalone/TctAppPackage/Launcher/res
    local attrs=vendor/tctalone/TctAppPackage/Launcher/res/values/attrs.xml
    local wallpaper=vendor/tctalone/TctAppPackage/Launcher/res/values/extra_wallpapers.xml
    local wallpaper_operator=vendor/tctalone/TctAppPackage/Launcher/res/values/extral_wallpapers_operator.xml

    #modify by kexin.li@tcl.com
    if [ -f "$TOP/$workspace/$TARGET_PRODUCT/xml/jrd_default_workspace.xml" ] ; then
        mkdir -p $JRD_CUSTOM_RES/$workspace/xml
        mkdir -p $JRD_CUSTOM_RES/$workspace/xml-hdpi
        mkdir -p $JRD_CUSTOM_RES/$workspace/xml-xhdpi
        mkdir -p $JRD_CUSTOM_RES/$workspace/xml-xxhdpi
        cp -f $TOP/$workspace/$TARGET_PRODUCT/xml/jrd_default_workspace.xml $JRD_CUSTOM_RES/$workspace/xml/jrd_default_workspace.xml
        cp -f $TOP/$workspace/$TARGET_PRODUCT/xml/jrd_default_workspace.xml $JRD_CUSTOM_RES/$workspace/xml-hdpi/jrd_default_workspace.xml
        cp -f $TOP/$workspace/$TARGET_PRODUCT/xml/jrd_default_workspace.xml $JRD_CUSTOM_RES/$workspace/xml-xhdpi/jrd_default_workspace.xml
        cp -f $TOP/$workspace/$TARGET_PRODUCT/xml/jrd_default_workspace.xml $JRD_CUSTOM_RES/$workspace/xml-xxhdpi/jrd_default_workspace.xml
        cp -f $TOP/$workspace/$TARGET_PRODUCT/xml/jrd_default_workspace_operator.xml $JRD_CUSTOM_RES/$workspace/xml/jrd_default_workspace_operator.xml
        cp -f $TOP/$workspace/$TARGET_PRODUCT/xml/jrd_default_workspace_operator.xml $JRD_CUSTOM_RES/$workspace/xml-hdpi/jrd_default_workspace_operator.xml
        cp -f $TOP/$workspace/$TARGET_PRODUCT/xml/jrd_default_workspace_operator.xml $JRD_CUSTOM_RES/$workspace/xml-xhdpi/jrd_default_workspace_operator.xml
        cp -f $TOP/$workspace/$TARGET_PRODUCT/xml/jrd_default_workspace_operator.xml $JRD_CUSTOM_RES/$workspace/xml-xxhdpi/jrd_default_workspace_operator.xml
    elif [ -f "$TOP/$workspace/xml/jrd_default_workspace.xml" ] ; then
        mkdir -p $JRD_CUSTOM_RES/$workspace/xml
        mkdir -p $JRD_CUSTOM_RES/$workspace/xml-hdpi
        mkdir -p $JRD_CUSTOM_RES/$workspace/xml-xhdpi
        mkdir -p $JRD_CUSTOM_RES/$workspace/xml-xxhdpi
        cp -f $TOP/$workspace/xml/jrd_default_workspace.xml $JRD_CUSTOM_RES/$workspace/xml/jrd_default_workspace.xml
        cp -f $TOP/$workspace/xml/jrd_default_workspace.xml $JRD_CUSTOM_RES/$workspace/xml-hdpi/jrd_default_workspace.xml
        cp -f $TOP/$workspace/xml/jrd_default_workspace.xml $JRD_CUSTOM_RES/$workspace/xml-xhdpi/jrd_default_workspace.xml
        cp -f $TOP/$workspace/xml/jrd_default_workspace.xml $JRD_CUSTOM_RES/$workspace/xml-xxhdpi/jrd_default_workspace.xml
        cp -f $TOP/$workspace/xml/jrd_default_workspace_operator.xml $JRD_CUSTOM_RES/$workspace/xml/jrd_default_workspace_operator.xml
        cp -f $TOP/$workspace/xml/jrd_default_workspace_operator.xml $JRD_CUSTOM_RES/$workspace/xml-hdpi/jrd_default_workspace_operator.xml
        cp -f $TOP/$workspace/xml/jrd_default_workspace_operator.xml $JRD_CUSTOM_RES/$workspace/xml-xhdpi/jrd_default_workspace_operator.xml
        cp -f $TOP/$workspace/xml/jrd_default_workspace_operator.xml $JRD_CUSTOM_RES/$workspace/xml-xxhdpi/jrd_default_workspace_operator.xml
    fi

    if [ -f "$TOP/$attrs" ] ; then
        mkdir -p $(dirname $JRD_CUSTOM_RES/$attrs)
        cp -f $TOP/$attrs $JRD_CUSTOM_RES/$attrs
    fi
    if [ -f "$TOP/$wallpaper" ] && [ ! -f $JRD_CUSTOM_RES/$wallpaper ] ; then
        cp -f $TOP/$wallpaper $JRD_CUSTOM_RES/$wallpaper
    fi
    if [ -f "$TOP/$wallpaper_operator" ] && [ ! -f $JRD_CUSTOM_RES/$wallpaper_operator ] ; then
        cp -f $TOP/$wallpaper_operator $JRD_CUSTOM_RES/$wallpaper_operator
    fi
    trap - ERR
}

function prepare_sign_tool {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    echo "prepare test-key tool"
    mkdir -p $TOP/out/host/linux-x86/framework
    cp $SCRIPTS_DIR/tools/signapk.jar $TOP/out/host/linux-x86/framework
    chmod 755 $TOP/out/host/linux-x86/framework/signapk.jar
    trap - ERR
}

function prepare_wifi {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    echo "now building the wifi files"
    override_exist_file $JRD_OUT_SYSTEM/etc/wifi/wpa_supplicant.conf $TOP/device/tct/$TARGET_PRODUCT/wpa_supplicant.conf
    trap - ERR
}

function prepare_btc {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    echo "now building the btc files"
    override_exist_file $JRD_OUT_SYSTEM/etc/wifi/WCNSS_qcom_cfg.ini $TOP/device/tct/$TARGET_PRODUCT/WCNSS_qcom_cfg.ini
    trap - ERR
}

function prepare_nfc {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    echo "now building the nfc files"
    override_exist_file $JRD_OUT_SYSTEM/etc/libnfc-brcm.conf $TOP/device/tct/$TARGET_PRODUCT/nfc/libnfc-brcm.conf
    trap - ERR
}

function prepare_plmn {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    echo "now building the plmn files"
    override_exist_file $JRD_OUT_CUSTPACK/plmn-list.conf $JRD_WIMDATA/wcustores/plmn-list.conf
    trap - ERR
}

function prepare_apn {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    echo "now building the apn files"
    override_exist_file $JRD_OUT_SYSTEM/etc/apns-conf.xml $JRD_WIMDATA/wcustores/apns-conf.xml
    trap - ERR
}

function prepare_gid_config {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    echo "now building gid config files"
    if [ -d $JRD_OUT_CUSTPACK/operator-gid ];then
        rm -rf $JRD_OUT_CUSTPACK/operator-gid/*.txt
    else
        mkdir -p $JRD_OUT_CUSTPACK/operator-gid
    fi
    if [ -e $JRD_WIMDATA/wcustores/App/$TARGET_PRODUCT/operator-gid/default.txt ];then
        cp -f $JRD_WIMDATA/wcustores/App/$TARGET_PRODUCT/operator-gid/*.txt $JRD_OUT_CUSTPACK/operator-gid
    else
        rm -rf $JRD_OUT_CUSTPACK/app/operator
        rm -rf $JRD_OUT_CUSTPACK/operator-gid
        echo "nothing gid config files"
    fi
    trap - ERR
}

function get_product_aapt_config {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    local language_list=$1
    set -x
    local default_aapt_config="normal,xxhdpi,xhdpi,hdpi,nodpi,anydpi"
    if [ -n "$language_list" ] ; then
        echo $(echo ${language_list[@]} | tr -s [:space:] ',')$default_aapt_config
    else
        echo "PRODUCT_LOCALES in this perso is NULL, exiting now ... "
        exit 1
    fi
    set +x
    trap - ERR
}

function replace_properties {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    local prop=$1
    local new_value=$2
    local origin=$3
    local target=$4

    origin_prop_value_pair=`echo "$origin" | grep -e "^$prop=" | head -n 1`
    origin_value=${origin_prop_value_pair#$prop=}
    if [ "$origin_value" != "$new_value" ] ; then
        set -x
        echo "replace value for $prop"
        origin_prop_value_pair=${origin_prop_value_pair//\//\\\/}
        new_value=${new_value//\//\\\/}
        #TODO: the prop value can't contain '/', '\'.
        sed -i -e 's/'"$origin_prop_value_pair"'/'$prop'='"$new_value"'/' $target
        set +x
    fi
    trap - ERR
}

# build.prop is combined by four parts:
#   1. from build/tools/buildinfo.sh
#   2. from device/tct/$product/system.prop
#   3. from Jrd_sys_properties.prop
#   4. from ADDITIONAL_BUILD_PROPERTIES defined in *.mk
function prepare_build_prop {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR

    echo "Now buiding build.prop ... "
    local build_prop=$JRD_OUT_SYSTEM/build.prop
    local jrd_build_prop_mk=$JRD_CUSTOM_RES/jrd_build_properties.mk
    local jrd_sys_prop=$JRD_CUSTOM_RES/jrd_sys_properties.prop
    if [ ! -f "$build_prop" ] || [ ! -f "$jrd_build_prop_mk" ] || [ ! -f "$jrd_sys_prop" ] ; then
        echo "can't find build.prop file, exiting now ..."
        exit
    fi
    # replace properties from jrd_build_properties.mk, which generated by buildinfo.sh generally
    local PRODUCT_MODEL=$(read_variable_from_makefile_space "PRODUCT_MODEL" $jrd_build_prop_mk)
    local PRODUCT_BRAND=$(read_variable_from_makefile "PRODUCT_BRAND" $jrd_build_prop_mk)
    local PRODUCT_MANUFACTURER=$(read_variable_from_makefile_space "PRODUCT_MANUFACTURER" $jrd_build_prop_mk)
    # PR 903236 SH SW4 Framework - Lan.Shan - lan.shan@jrdcom.com 67424 - 2015-1-27 Add Begin
    # [Bug Fix] Customize TCT_PRODUCT_DEVICE
    local TCT_PRODUCT_DEVICE=$TARGET_PRODUCT
    if [ "$TARGET_PRODUCT" == "idol347" ] ; then
        TCT_PRODUCT_DEVICE=$(read_variable_from_makefile "TCT_PRODUCT_DEVICE" $jrd_build_prop_mk)
    fi
    # PR 903236 SH SW4 Framework - Lan.Shan - lan.shan@jrdcom.com 67424 - 2015-1-27 Add End
    local TCT_BUILD_NUMBER=$(read_variable_from_makefile "def_tctfw_build_number" $jrd_build_prop_mk)
    local TCT_PRODUCT_NAME=$(echo $PRODUCT_MODEL | sed -e 's/ /_/g')
    local TARGET_DEVICE=$(get_build_var "TARGET_DEVICE")
    local PLATFORM_VERSION=$(get_build_var "PLATFORM_VERSION")
    local BUILD_ID=$(get_build_var "BUILD_ID")
    local BUILD_NUMBER=$(get_build_var "BUILD_NUMBER")
    local BUILD_FINGERPRINT=${PRODUCT_BRAND}/${TCT_PRODUCT_NAME}/${TARGET_DEVICE}:${PLATFORM_VERSION}/${BUILD_ID}/${BUILD_NUMBER}:${TARGET_BUILD_VARIANT}/release-keys

    origin_build_prop=$(cat $build_prop)
    replace_properties "ro.product.model" "$PRODUCT_MODEL" "$origin_build_prop" $build_prop
    replace_properties "ro.product.name" "$TCT_PRODUCT_NAME" "$origin_build_prop" $build_prop
    replace_properties "ro.product.brand" "$PRODUCT_BRAND" "$origin_build_prop" $build_prop
    # PR 903236 SH SW4 Framework - Lan.Shan - lan.shan@jrdcom.com 67424 - 2015-1-27 Add Begin
    # [Bug Fix] Customize TCT_PRODUCT_DEVICE
    replace_properties "ro.product.device" "$TCT_PRODUCT_DEVICE" "$origin_build_prop" $build_prop
    # PR 903236 SH SW4 Framework - Lan.Shan - lan.shan@jrdcom.com 67424 - 2015-1-27 Add End
    replace_properties "def.tctfw.build.number" "$TCT_BUILD_NUMBER" "$origin_build_prop" $build_prop
    replace_properties "ro.build.product" "$TARGET_PRODUCT" "$origin_build_prop" $build_prop
    replace_properties "ro.product.manufacturer" "$PRODUCT_MANUFACTURER" "$origin_build_prop" $build_prop
    replace_properties "ro.build.date" "`date`" "$origin_build_prop" $build_prop
    replace_properties "ro.build.date.utc" "`date +%s`" "$origin_build_prop" $build_prop
    replace_properties "ro.build.user" "$USER" "$origin_build_prop" $build_prop
    replace_properties "ro.build.host" "`hostname`" "$origin_build_prop" $build_prop
    replace_properties "ro.tct.product" "$TARGET_PRODUCT" "$origin_build_prop" $build_prop
    replace_properties "ro.build.fingerprint" "$BUILD_FINGERPRINT" "$origin_build_prop" $build_prop

    #TODO: check other prop
    #replace_properties "ro.build.description" `date +%s` $origin_build_prop $build_prop
    #replace_properties "ro.build.display.id" `date +%s` $origin_build_prop $build_prop

    # replace properties from jrd_sys_properties.prop
    cat $jrd_sys_prop | while read -r readline
    do
        if [ $(echo $readline | grep -o -e "^[^#]*=") ] ; then
            local prop=$(echo $readline | cut -d'=' -f1)
            local value=${readline#$prop=}
            value=$(echo $value | tr -d '\r\n')
            sed -i -e /$prop=.*/d $build_prop ;
        fi
    done
    cat $jrd_sys_prop | tee -a $build_prop

    trap - ERR
}

function prepare_theme {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    #TODO: build theme packages.
    echo "now copy the theme"
    clean_intermediates_folder $THEME_OUT_PATH/theme
    mkdir -p $THEME_OUT_PATH/theme
    cp -rf $THEME_RESOUCE_PATH/* $THEME_OUT_PATH/theme
    trap - ERR
}

function prepare_usermanual {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    echo "now building the customized user manuals..."
    override_exist_folder $JRD_OUT_CUSTPACK/JRD_custres/user_manual $JRD_WIMDATA/wcustores/UserManual
    trap - ERR
}

function prepare_device_config_xml {
    # Prepare device configration xmls, like, NFC/COMPASS, etc.
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR

    local nfc_items=(app/NfcNci \
                     app/SmartcardService \
                     app/TctGsmaService \
                     etc/permissions/android.hardware.nfc.xml \
                     etc/permissions/android.hardware.nfc.hce.xml \
                     lib/libnfc-nci.so \
                     lib/libnfc_nci_jni.so \
                     lib/libnfctester_jni.so \
                     lib/hw/nfc_nci.bcm2079x.default.so \
                     framework/org.simalliance.openmobileapi.jar \
                     framework/com.gsma.services.nfc.jar )

    # remove nfc conf files when nfc disabled
    local nfc_enable=$(grep "ro.kernel.nfc.enable" $JRD_OUT_SYSTEM/build.prop | cut -d"=" -f2 | tr -d '\r')
    if [ "$nfc_enable" == "false" ] ; then
        for nfc_item in ${nfc_items[@]}
        do
            if [ -d "$JRD_OUT_SYSTEM/$nfc_item" -o -f "$JRD_OUT_SYSTEM/$nfc_item" ] ; then
                rm -rf $JRD_OUT_SYSTEM/$nfc_item
            fi
        done
    fi
    # remove compass sensor from handheld_core_hardware.xml when compass disabled
    local compass_enable=$(grep "ro.kernel.compass.enable" $JRD_OUT_SYSTEM/build.prop | cut -d"=" -f2 | tr -d '\r')
    if [ "$compass_enable" == "false" ] ; then
        sed -i /android.hardware.sensor.compass/d $JRD_OUT_SYSTEM/etc/permissions/handheld_core_hardware.xml
    fi
    # remove gyroscope conf files when gyroscope disabled
    local gyroscope_enable=$(grep "ro.hardware.gyroscope.enable" $JRD_OUT_SYSTEM/build.prop | cut -d"=" -f2 | tr -d '\r')
    if [ "$gyroscope_enable" == "false" ] ; then
        rm -f $JRD_OUT_SYSTEM/etc/permissions/android.hardware.sensor.gyroscope.xml
    fi
    trap - ERR
}

function get_package_name {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    if [ -d "$2/$3" ] ; then
        if [ -f "$1/$3/AndroidManifest.xml" ] ; then
            cat $1/$3/AndroidManifest.xml | grep -o -e 'package="[_0-9a-zA-Z.]*"' | cut -d'=' -f2 | tr -d \" | sed 's/\.overlay//'
        else
            apklist=($(find $1/$3 -type f -name *.apk))
            if [ ${#apklist[@]} -eq 1 ] ; then
                echo $($MY_AAPT_TOOL d --values permissions $apklist | head -n 1 | cut -d" " -f2)
            elif [ ${#apklist[@]} -lt 1 ] ; then
                echo "WARNNING:NO APK exist."
            else
                echo "ERROR:Duplicated APK exist."
                exit 1
            fi
        fi
    fi
    trap - ERR
}

function get_coreApp_attr {
    # Only coreApp attribute is true, then the overlay res apk can be loaded when phone userdata is encrypted.    
    #trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    if [ -f "$1/$3/AndroidManifest.xml" ] ; then
        echo $(xmlstarlet sel -t -m "/manifest"  -v "@coreApp" "$1/$3/AndroidManifest.xml")             
    fi
    #trap - ERR
}

function get_local_package_name {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    if [ -f "$1/Android.mk" ] ; then
        name=$(read_variable_from_makefile "LOCAL_PACKAGE_NAME" $1/Android.mk)
        # if more than one package name found, remove override package
        if [ $(echo $name | wc -w) -gt 1 ] ; then
            override=$(read_variable_from_makefile "LOCAL_OVERRIDES_PACKAGES" $1/Android.mk)
            if [ -n "$override" ] && [ "$(echo $name | grep $override)" ] ; then
                echo ${name/$override/}
            fi
        elif [ -z "$name" ] || [[ "$1" =~ "TctAppPackage" ]] ; then
            name=$(read_variable_from_makefile "LOCAL_MODULE" $1/Android.mk)
            echo $name
        else
            echo $name
        fi
    fi
    trap - ERR
}

function get_local_certificate {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    local is_privileged_module=""
    if [ -f "$1/Android.mk" ] ; then
        name=$(read_variable_from_makefile LOCAL_CERTIFICATE $1/Android.mk)

        if [ "$name" == "PRESIGNED" ] && [[ "$1" =~ "TctAppPackage" ]] ; then
            is_privileged_module=$(read_variable_from_makefile "LOCAL_PRIVILEGED_MODULE" $1/Android.mk)
            if [ "$is_privileged_module" == "true" ] ; then
                name=platform
            else
                name=releasekey
            fi
        fi

        if [ $(echo $name | wc -w) -gt 1 ] ; then
            override=$(read_variable_from_makefile LOCAL_OVERRIDES_PACKAGES $1/Android.mk)
            if [ -n "$override" ] && [ "$(echo $name | grep $override)" ] ; then
                echo ${name/$override/}
            fi
        else
            if [ -n "$name" ] ; then
                echo $name
            else
                echo "releasekey"
            fi
        fi
    fi
    trap - ERR
}

function process_sys_plf {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    #generate the jrd_sys_properties.prop & jrd_build_properties.mk
    $JRD_BUILD_PATH/common/perso/process_sys_plf.sh $JRD_TOOLS_ARCT $JRD_PROPERTIES_PLF $JRD_CUSTOM_RES 1>/dev/null
    trap - ERR
}

function read_variable_from_makefile {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    # read in the makefile, and find out the value of the give variable
    # $1 target variable to found
    # $2 target file to search
    if [ -z "$1" ] || [ -z "$2" ] ; then
        echo "input parameters cannot be null" >> read_variable_error.log
        return
    fi
    local result=
    local variable=$1
    local findit="false"
    if [ -f $2 ] ; then
        local count=($(grep -E -n "$variable\s*:=" $2 | cut -d":" -f1))
        local linenum=${count[${#count[@]}-1]}

        if [ ${#count[@]} -eq 0 ] ; then
            echo "Cannot find $variable in $2" >> read_variable_error.log
            echo ""
            return
        else
            linenum=${count[${#count[@]}-1]}
        fi

        #cat $2 | grep -v "^#" | while read -r readline
        sed -n "$linenum,\$p" $2 | grep -v "^#" | grep -v "^\s*$" | while read -r readline
        do
            readline=$(echo $readline | tr -d [:space:]) # remove space
            if [ "$findit" == "false" ] ; then
                if [[ "$readline" =~ ^\s*$variable\s*:=.* ]] ; then
                    findit="true"
                    if [ "${readline: -1}" == "\\" ] ; then
                        readline=$(echo $readline | tr -d '\\')
                        if [ $(echo $readline | grep -o -e "=") ] ; then
                            echo $readline | cut -d '=' -f2 >> result.txt
                        fi
                    else
                        if [ $(echo $readline | grep -o -e "=") ] ; then
                            echo $readline | cut -d '=' -f2 >> result.txt
                            findit="false"
                            break
                        fi
                    fi
                fi
            else
                #echo $readline
                if [ "${readline: -1}" == "\\" ] ; then
                    readline=$(echo $readline | tr -d '\\')
                    echo $readline >> result.txt
                else
                    echo $readline >> result.txt
                    findit="false"
                    break
                fi
            fi
        done
    fi

    if [ -f result.txt ] ; then
        result=$(cat result.txt | sed 's/#[^#]*//g')
        rm -f result.txt
    fi
    echo $result
    trap - ERR
}

function read_variable_from_makefile_space {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    # read in the makefile, and find out the value of the give variable
    # $1 target variable to found
    # $2 target file to search
    if [ -z "$1" ] || [ -z "$2" ] ; then
        echo "input parameters cannot be null" >> read_variable_error.log
        return
    fi
    local result=
    local variable=$1
    local findit="false"
    if [ -f $2 ] ; then
        local count=($(grep -E -n "$variable\s*:=" $2 | cut -d":" -f1))
        local linenum=${count[${#count[@]}-1]}

        if [ ${#count[@]} -eq 0 ] ; then
            echo "Cannot find $variable in $2" >> read_variable_error.log
            echo ""
            return
        else
            linenum=${count[${#count[@]}-1]}
        fi

        #cat $2 | grep -v "^#" | while read -r readline
        sed -n "$linenum,\$p" $2 | grep -v "^#" | grep -v "^\s*$" | while read -r readline
        do
            #readline=$(echo $readline | tr -d [:space:]) # remove space
            if [ "$findit" == "false" ] ; then
             #   if [[ "$readline" =~ ^\s*$variable\s*:=.* ]] ; then
                    findit="true"
                    if [ "${readline: -1}" == "\\" ] ; then
                        readline=$(echo $readline | tr -d '\\')
                        if [ $(echo $readline | grep -o -e "=") ] ; then
                            echo $readline | cut -d '=' -f2 >> result_space.txt
                        fi
                    else
                        if [ $(echo $readline | grep -o -e "=") ] ; then
                            echo $readline | cut -d '=' -f2 >> result_space.txt
                            findit="false"
                            break
                        fi
                    fi
        #        fi
            else
                #echo $readline
                if [ "${readline: -1}" == "\\" ] ; then
                    readline=$(echo $readline | tr -d '\\')
                    echo $readline >> result_space.txt
                else
                    echo $readline >> result_space.txt
                    findit="false"
                    break
                fi
            fi
        done
    fi

    if [ -f result_space.txt ] ; then
        result=$(cat result_space.txt | sed 's/#[^#]*//g' | sed 's/\r//g')
        rm -f result_space.txt
    fi
    echo $result
    trap - ERR
}

function generate_androidmanifest_xml {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    echo "Generate AndroidManifest.xml..."
    if [ -n "$1" ] && [ -d $2 ] ; then
        if [ -z "$3" ] ; then
            echo '<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="'$1'.overlay">
    <overlay android:targetPackage="'$1'" android:priority="16"/>
</manifest>' > $2/AndroidManifest.xml
        else
            echo '<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="'$1'.overlay"
    coreApp="true">
    <overlay android:targetPackage="'$1'" android:priority="16"/>
</manifest>' > $2/AndroidManifest.xml
        fi
    fi
    trap - ERR
}

function prepare_audio_param {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    echo "copy audio params"
    if [ "$TARGET_PRODUCT" != "idol347" ] ; then
        cp -f $JRD_PROPERTIES_AUDIO/Bluetooth_cal.acdb $JRD_OUT_SYSTEM/etc/acdbdata/MTP/MTP_Bluetooth_cal.acdb
        cp -f $JRD_PROPERTIES_AUDIO/General_cal.acdb $JRD_OUT_SYSTEM/etc/acdbdata/MTP/MTP_General_cal.acdb
        cp -f $JRD_PROPERTIES_AUDIO/Global_cal.acdb $JRD_OUT_SYSTEM/etc/acdbdata/MTP/MTP_Global_cal.acdb
        cp -f $JRD_PROPERTIES_AUDIO/Handset_cal.acdb $JRD_OUT_SYSTEM/etc/acdbdata/MTP/MTP_Handset_cal.acdb
        cp -f $JRD_PROPERTIES_AUDIO/Hdmi_cal.acdb $JRD_OUT_SYSTEM/etc/acdbdata/MTP/MTP_Hdmi_cal.acdb
        cp -f $JRD_PROPERTIES_AUDIO/Headset_cal.acdb $JRD_OUT_SYSTEM/etc/acdbdata/MTP/MTP_Headset_cal.acdb
        cp -f $JRD_PROPERTIES_AUDIO/Speaker_cal.acdb $JRD_OUT_SYSTEM/etc/acdbdata/MTP/MTP_Speaker_cal.acdb
        cp -f $JRD_PROPERTIES_AUDIO_SmartPA/seltech_stereo.ini $JRD_OUT_SYSTEM/etc/tfa9897/seltech_stereo.ini
        cp -f $JRD_PROPERTIES_AUDIO_SmartPA/seltech_stereo.cnt $JRD_OUT_SYSTEM/etc/tfa9897/seltech_stereo.cnt
        cp -f $JRD_PROPERTIES_AUDIO_SmartPA/seltech_top.ini $JRD_OUT_SYSTEM/etc/tfa9897/seltech_top.ini
        cp -f $JRD_PROPERTIES_AUDIO_SmartPA/seltech_top.cnt $JRD_OUT_SYSTEM/etc/tfa9897/seltech_top.cnt
        cp -f $JRD_PROPERTIES_AUDIO_SmartPA/seltech_bottom.ini $JRD_OUT_SYSTEM/etc/tfa9897/seltech_bottom.ini
        cp -f $JRD_PROPERTIES_AUDIO_SmartPA/seltech_bottom.cnt $JRD_OUT_SYSTEM/etc/tfa9897/seltech_bottom.cnt
        #AUDIO_EFFECT Customization
        mv $AUDIO_EFFECT_PATH/libarkamys.so $JRD_OUT_SYSTEM/lib/soundfx/libarkamys.so
        mv $AUDIO_EFFECT_PATH/volume_table $JRD_OUT_SYSTEM/etc/arkamys/volume_table
        rm -rf $JRD_OUT_SYSTEM/etc/arkamys/config_presets/*
        cp -rf $AUDIO_EFFECT_PATH/* $JRD_OUT_SYSTEM/etc/arkamys/config_presets/
    fi
    if [ -f $JRD_WIMDATA/wcustores/objective ] ; then
        cp -f $JRD_WIMDATA/wcustores/audio_params/$TARGET_PRODUCT/TMO_TEL_TST/SMARTPA/AAC/seltech_bottom.cnt $JRD_OUT_SYSTEM/etc/tfa9897/AAC/seltech_bottom.cnt
        cp -f $JRD_WIMDATA/wcustores/audio_params/$TARGET_PRODUCT/TMO_TEL_TST/SMARTPA/AAC/seltech_stereo.cnt $JRD_OUT_SYSTEM/etc/tfa9897/AAC/seltech_stereo.cnt
	cp -f $JRD_WIMDATA/wcustores/audio_params/$TARGET_PRODUCT/TMO_TEL_TST/SMARTPA/AAC/seltech_top.cnt $JRD_OUT_SYSTEM/etc/tfa9897/AAC/seltech_top.cnt
	cp -f $JRD_WIMDATA/wcustores/audio_params/$TARGET_PRODUCT/TMO_TEL_TST/SMARTPA/LC/seltech_bottom.cnt $JRD_OUT_SYSTEM/etc/tfa9897/LC/seltech_bottom.cnt
	cp -f $JRD_WIMDATA/wcustores/audio_params/$TARGET_PRODUCT/TMO_TEL_TST/SMARTPA/LC/seltech_stereo.cnt $JRD_OUT_SYSTEM/etc/tfa9897/LC/seltech_stereo.cnt
	cp -f $JRD_WIMDATA/wcustores/audio_params/$TARGET_PRODUCT/TMO_TEL_TST/SMARTPA/LC/seltech_top.cnt $JRD_OUT_SYSTEM/etc/tfa9897/LC/seltech_top.cnt
        cp -f $JRD_WIMDATA/wcustores/audio_params/$TARGET_PRODUCT/TMO_TEL_TST/ACDB/MTP_Bluetooth_cal.acdb $JRD_OUT_SYSTEM/etc/acdbdata/MTP/MTP_Bluetooth_cal.acdb
        cp -f $JRD_WIMDATA/wcustores/audio_params/$TARGET_PRODUCT/TMO_TEL_TST/ACDB/MTP_General_cal.acdb $JRD_OUT_SYSTEM/etc/acdbdata/MTP/MTP_General_cal.acdb
	cp -f $JRD_WIMDATA/wcustores/audio_params/$TARGET_PRODUCT/TMO_TEL_TST/ACDB/MTP_Global_cal.acdb $JRD_OUT_SYSTEM/etc/acdbdata/MTP/MTP_Global_cal.acdb
	cp -f $JRD_WIMDATA/wcustores/audio_params/$TARGET_PRODUCT/TMO_TEL_TST/ACDB/MTP_Handset_cal.acdb $JRD_OUT_SYSTEM/etc/acdbdata/MTP/MTP_Handset_cal.acdb
	cp -f $JRD_WIMDATA/wcustores/audio_params/$TARGET_PRODUCT/TMO_TEL_TST/ACDB/MTP_Hdmi_cal.acdb $JRD_OUT_SYSTEM/etc/acdbdata/MTP/MTP_Hdmi_cal.acdb
	cp -f $JRD_WIMDATA/wcustores/audio_params/$TARGET_PRODUCT/TMO_TEL_TST/ACDB/MTP_Headset_cal.acdb $JRD_OUT_SYSTEM/etc/acdbdata/MTP/MTP_Headset_cal.acdb
	cp -f $JRD_WIMDATA/wcustores/audio_params/$TARGET_PRODUCT/TMO_TEL_TST/ACDB/MTP_Speaker_cal.acdb $JRD_OUT_SYSTEM/etc/acdbdata/MTP/MTP_Speaker_cal.acdb
    fi
    trap - ERR
}

function get_custo_apk_path {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    local is_privileged_module=
    local my_module_path=
    #echo "Try to get overlay package installation path"
    if [ -f $1/Android.mk ] ; then
        is_privileged_module=$(read_variable_from_makefile "LOCAL_PRIVILEGED_MODULE" $1/Android.mk)
        my_module_path=$(read_variable_from_makefile "LOCAL_MODULE_PATH" $1/Android.mk)
        if [ -n "$my_module_path" ] ; then
            my_module_path=$(echo $my_module_path | sed -e 's/(//g' -e 's/)//g' | grep -o "\$[A-Z_]*[-/a-z]*")
            my_module_path=$(eval "echo $my_module_path")
            if [[ ! "$my_module_path" =~ "system/framework" ]] && [[ ! "$my_module_path" =~ "system/app" ]] && [[ ! "$my_module_path" =~ "system/priv-app" ]] && [[ ! "$my_module_path" =~ "system/custpack/app" ]] ; then
                my_module_path=
            fi
        else
            my_module_path=
        fi
    fi

    if [ "$is_privileged_module" == "true" ] ; then
        echo $JRD_OUT_SYSTEM/priv-app
    else
        if [ -n "$my_module_path" -a -d "$my_module_path" ] ; then
            echo $my_module_path
        else
            echo $JRD_OUT_SYSTEM/app
        fi
    fi
    trap - ERR
}

function prepare_overlay_res {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    if [ -z "$DEBUG_ONLY" ] ; then
        prepare_translations
        prepare_res_config
    fi
    if ( $TARGET_BUILD_CUSTOM_IMAGES ) ; then
        prepare_photos
    fi
    prepare_media
    prepare_ringtone
    #prepare_fonts
    prepare_usermanual
    prepare_apn
    prepare_plmn
    prepare_wifi
    prepare_btc
    prepare_nfc
    #prepare_theme
    find_res_dir $JRD_BUILD_PATH_DEVICE/perso/string_res.ini
    prepare_launcher_workspace
    prepare_plfs
    process_sys_plf # process isdm_sys_properties.plf
    prepare_build_prop
    prepare_sign_tool
    trap - ERR
}

function remove_extra_apk {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    set -x
    # remove apks in /system/app or /system/priv-app, when apk isdm value is "0" in isdm_sys_properties.plf
    for apk in ${JRD_PRODUCT_PACKAGES[@]}
    do
        if [ -d "$JRD_OUT_SYSTEM/app/$apk" ] ; then
            rm -rf $JRD_OUT_SYSTEM/app/$apk
            echo "apkfile_name: $JRD_OUT_SYSTEM/app/$apk/$apk.apk" >> remove_apks.log
        elif [ -d "$JRD_OUT_SYSTEM/priv-app/$apk" ] ; then
            rm -rf $JRD_OUT_SYSTEM/priv-app/$apk
            echo "apkfile_name: $JRD_OUT_SYSTEM/priv-app/$apk/$apk.apk" >> remove_apks.log
        elif [ -d "$JRD_OUT_CUSTPACK/app/removeable/$apk" ] ; then
            rm -rf $JRD_OUT_CUSTPACK/app/removeable/$apk
            echo "apkfile_name: $JRD_OUT_CUSTPACK/app/removeable/$apk/$apk.apk" >> remove_apks.log
        elif [ -d "$JRD_OUT_CUSTPACK/app/unremoveable/$apk" ] ; then
            rm -rf $JRD_OUT_CUSTPACK/app/unremoveable/$apk
            echo "apkfile_name: $JRD_OUT_CUSTPACK/app/unremoveable/$apk/$apk.apk" >> remove_apks.log
        elif [ -f "$JRD_OUT_SYSTEM/app/$apk.apk" ] ; then
            rm -f $JRD_OUT_SYSTEM/app/$apk.apk
            echo "apkfile_name: $JRD_OUT_SYSTEM/app/$apk.apk" >> remove_apks.log
        elif [ -f "$JRD_OUT_SYSTEM/priv-app/$apk.apk" ] ; then
            rm -f $JRD_OUT_SYSTEM/priv-app/$apk.apk
            echo "apkfile_name: $JRD_OUT_SYSTEM/priv-app/$apk.apk" >> remove_apks.log
        elif [ -f "$JRD_OUT_CUSTPACK/app/removeable/$apk.apk" ] ; then
            rm -f $JRD_OUT_CUSTPACK/app/removeable/$apk.apk
            echo "apkfile_name: $JRD_OUT_CUSTPACK/app/removeable/$apk.apk" >> remove_apks.log
        elif [ -f "$JRD_OUT_CUSTPACK/app/unremoveable/$apk.apk" ] ; then
            rm -f $JRD_OUT_CUSTPACK/app/unremoveable/$apk.apk
            echo "apkfile_name: $JRD_OUT_CUSTPACK/app/unremoveable/$apk.apk" >> remove_apks.log
        else
            echo "WARNING:CANNOT find $apk in /system"
            continue
        fi
    done
    set +x
    trap - ERR
}

function generate_overlay_packages {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    # parse string_res.ini, to find out all packages that need generate overlay apk
    # TODO: string_res.ini only include packages need to be translated, but still there is some pacages use google default translation.

    #create folders for overlay apk
    local my_apk_path=$TARGET_OUT_VENDOR_OVERLAY
    local my_package_name
    local my_apk_file_name
    local my_apk_certificate
    local main_apk_path
    local extra_res
    local extra_res_list
    local item

    clean_intermediates_folder $TARGET_OUT_VENDOR_OVERLAY

    if [ ! -d "$my_apk_path" ] ; then
        mkdir -p $my_apk_path
    fi

    if [ -f "$JRD_CUSTOM_RES/jrd_build_properties.mk" ] ;then
        PRODUCT_LOCALES=$(read_variable_from_makefile "PRODUCT_LOCALES" $JRD_CUSTOM_RES/jrd_build_properties.mk)
    else
        echo "Can't find jrd_build_properties.mk, exiting now ... "
        exit 1
    fi

    PRODUCT_AAPT_CONFIG=$(get_product_aapt_config "$PRODUCT_LOCALES")
    prepare_timezone $PRODUCT_LOCALES

    local MY_ASSET_OPT=

    for res in $MY_RES_DIR
    do
        res=$(dirname $res)
        echo "Start to process ---- $res ----"
        my_apk_file_name=$(get_local_package_name $TOP/$res)
        main_apk_path=$(get_custo_apk_path $TOP/$res)

        if [ ! -f "$main_apk_path/$my_apk_file_name/${my_apk_file_name}.apk" ] && [ ! -f "$main_apk_path/${my_apk_file_name}.apk" ] ; then
            echo "$res/res" >> ungene_package.log
            echo "main_apk_path: $main_apk_path" >> ungene_package.log
            echo "apkfile_name: $my_apk_file_name" >> ungene_package.log
            continue
        fi

        my_package_name=$(get_package_name $TOP $JRD_CUSTOM_RES $res)
        coreAppAttr=$(get_coreApp_attr $TOP $JRD_CUSTOM_RES $res)

        if [ -n "$my_package_name" ] && [ -n "$my_apk_file_name" ] ; then

            my_tmp_path=$JRD_CUSTOM_RES/$res
            if [ -d "$my_tmp_path" ] ; then
                mkdir -p $my_tmp_path
            fi

            generate_androidmanifest_xml $my_package_name $my_tmp_path $coreAppAttr

            if ( grep "<package name=\"$my_apk_file_name\">" $SCRIPTS_DIR/package_list.xml ) ; then
                extra_res_list=$(xmlstarlet sel -t -m "/package_list/package[@name='$my_apk_file_name']/res" -o " $JRD_CUSTOM_RES/" -v "@path" $SCRIPTS_DIR/package_list.xml)
                extra_res=""
                for item in $extra_res_list
                do
                    if [ -d "$item" ] ; then
                        extra_res="$extra_res -S $item"
                    fi
                done
                if [ -n "$extra_res" ] ; then
                    extra_res="--auto-add-overlay $extra_res"
                fi
            else
                extra_res=""
            fi

            #aapt p -f -S res -I /media/Ubuntu/dev/android-sdk-linux_x86/platforms/android-17/android.jar -A assets -M AndroidManifest.xml -F Settings-overlay.apk
            #1，android.jar需要使用平台的
            #2，如果没有asset文件夹，可以移除掉-A参数
            #3，替换资源包命名需要使用“APKNAME-Overlay.apk”方式
            #TODO: product_config
            if [ -d $JRD_CUSTOM_RES/$res/assets ] ; then
                MY_ASSET_OPT="-A $JRD_CUSTOM_RES/$res/assets"
            else
                MY_ASSET_OPT= 
            fi

            if [ -f $JRD_CUSTOM_RES/$res/AndroidManifest.xml ] ; then
                # TODO: check if overlay package generated or not?
                $MY_AAPT_TOOL p -f -I $MY_ANDROID_JAR_TOOL \
                    -S $JRD_CUSTOM_RES/$res/res \
                    $extra_res \
                    -M $JRD_CUSTOM_RES/$res/AndroidManifest.xml \
                    -c $PRODUCT_AAPT_CONFIG \
                    -F $my_tmp_path/$my_apk_file_name-overlay.apk $MY_ASSET_OPT > /dev/null

                if [ ! -f "$my_tmp_path/$my_apk_file_name-overlay.apk" ] ; then
                    echo "$my_tmp_path/$my_apk_file_name-overlay.apk generate failed" >> overlay-failed.log
                fi

                my_apk_certificate="releasekey"

                #TODO: It's ok to use releasekey for all overlay apk
                #my_apk_certificate=$(get_local_certificate $TOP/$res)
                my_apk_certificate="releasekey"

                #Try use jdk6 jarsigner to sign overlay apk, which is much faster then by using signapk.jar!
                if [ -d "/opt/java/jdk1.6.0_45" ] ; then
                    /opt/java/jdk1.6.0_45/bin/jarsigner -sigfile CERT -verbose \
                        -digestalg SHA1 -sigalg MD5withRSA \
                        -keystore $SCRIPTS_DIR/android.testkey \
                        -storepass TCL_1010 \
                        -signedjar $my_tmp_path/$my_apk_file_name-overlay-signed.apk \
                        $my_tmp_path/$my_apk_file_name-overlay.apk  \
                        android-testkey-key
                    zipalign -f -v 4 $my_tmp_path/$my_apk_file_name-overlay-signed.apk $my_apk_path/$my_apk_file_name-overlay.apk

                elif [ -n "$my_apk_certificate" ] ; then
                    java -Xmx128m -jar $TOP/out/host/linux-x86/framework/signapk.jar \
                        $TOP/android_perso_tool/scgng/TCT_releasekeys/$my_apk_certificate.x509.pem \
                        $TOP/android_perso_tool/scgng/TCT_releasekeys/$my_apk_certificate.pk8 \
                        $my_tmp_path/$my_apk_file_name-overlay.apk \
                        $my_apk_path/$my_apk_file_name-overlay.apk

                    if [ ! -f "$my_apk_path/$my_apk_file_name-overlay.apk" ] ; then
                        echo "$my_apk_path/$my_apk_file_name-overlay.apk sign failed" >> sign-failed.log
                    else
                        zipalign -c 4 $my_apk_path/$my_apk_file_name-overlay.apk
                        if [ $? -ne 0 ] ; then
                            zipalign -f 4 $my_apk_path/$my_apk_file_name-overlay.apk $my_apk_path/$my_apk_file_name-overlay.apk_aligned
                            if [ $? -eq 0 ] && [ -f "$my_apk_path/$my_apk_file_name-overlay.apk_aligned" ] ; then
                                rm -f $my_apk_path/$my_apk_file_name-overlay.apk
                                mv $my_apk_path/$my_apk_file_name-overlay.apk_aligned $my_apk_path/$my_apk_file_name-overlay.apk
                            fi
                        fi
                    fi
                fi
            fi
        else
            echo $res/res >> missing_package.log
            echo "package_name: $my_package_name" >> missing_package.log
            echo "apkfile_name: $my_apk_file_name" >> missing_package.log
        fi
    done

    trap - ERR
}

function change_system_ver {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    echo $PERSO_VERSION > $JRD_OUT_SYSTEM/system.ver
    trap - ERR
}

function release_key {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    bash $SCRIPTS_DIR/checkapk_perso.sh $JRD_OUT_CUSTPACK $TOP
    pushd $TOP > /dev/null
    bash $SCRIPTS_DIR/releasekey.sh "TCL_1010" $TARGET_PRODUCT
    popd > /dev/null
    trap - ERR
}

function generate_userdata_image {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    local userdata_image_size
    local extra_config=""
    if [ -z "$USERDATA_SIZE" ] ; then
        userdata_image_size=$(get_build_var "BOARD_USERDATAIMAGE_PARTITION_SIZE")
    else
        userdata_image_size=$USERDATA_SIZE
    fi
    if [ -f "$TARGET_ROOT_OUT/file_contexts" ] ; then
        extra_config="$TARGET_ROOT_OUT/file_contexts"
    else
        echo "cannot found file_contexts"
        exit 1
    fi
    echo "mkuserimg.sh -s $PRODUCT_OUT/data $PRODUCT_OUT/userdata.img ext4 data $userdata_image_size $extra_config"
    mkuserimg.sh -s $PRODUCT_OUT/data $PRODUCT_OUT/userdata.img ext4 data $userdata_image_size $extra_config
    trap - ERR
}

function generate_tarball {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    echo "Generate study.tar from the nv param management"
    mkdir -p $TARBALL_OUT_DIR
    python $AUTO_SCRIPTS_DIR/maketar.py $TARGET_PRODUCT $TARGET_BUILD_MMITEST $TOP/device/tct/$TARGET_PRODUCT/perso/isdm_nv_control.plf $TOP/device/tct/common/Build_Info.txt $TARBALL_OUT_DIR > /dev/null
    trap - ERR
}

function generate_splash_image {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    echo "Generate a splash.img from the picture"
    python $JRD_TOOLS/logo_gen/multi_logo_gen.py $PRODUCT_OUT/splash.img $TOP/device/tct/$TARGET_PRODUCT/logo.png $TOP/device/tct/$TARGET_PRODUCT/Dload_logo.png $TOP/device/tct/$TARGET_PRODUCT/Low_power_logo.png $TOP/device/tct/$TARGET_PRODUCT/Charger_boot_logo.png
    trap - ERR
}

function check_whitespace {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    echo "Check filename contains whitespace in system image ... "
    pushd $PRODUCT_OUT > /dev/null
    if (find system -type f | grep " "); then
        echo "ERROR: file contains whitespace character"
        exit 1
    fi
    popd > /dev/null
    trap - ERR
}

function umount_system_image {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    local keyword=$1
    mounted=($(df | grep $keyword | awk '{print $1}'))

    for device in ${mounted[@]}
    do
        sudo umount $device
        if [ $? -eq 0 ] ; then
            echo "umount $device succeed"
        else
            echo "umount $device failed"
            exit 1
        fi
    done

    local raw_file_name=$2
    if [ -n $raw_file_name ] && [ -f $raw_file_name ] ; then
        rm -f $raw_file_name
    fi
    trap - ERR
}

function mount_system_image {
    local dest_raw_file=$1
    local dest_path=$2
    local mygroup
    #mount the system image
    sudo mount -o loop $dest_raw_file $dest_path
    if [ $? -eq 0 ] ; then
        echo "mount $dest_raw_file succeed"
    else
        echo "mount $dest_raw_file failed"
        exit 1
    fi
    #get the name of current user group
    mygroup=$(echo $(groups) | awk '{print $1}')
    #change file owner and group to current user
    sudo chown -hR $USER:$mygroup $dest_path
    #remove lost+found folder
    if [ -d "$dest_path/lost+found" ] ; then
        rm -rf $dest_path/lost+found
    fi
}

function prepare_tools {
    if [ ! -f "$JRD_TOOLS/simg2img" ]; then
        cp $SCRIPTS_DIR/tools/simg2img $JRD_TOOLS/simg2img
        chmod 755 $JRD_TOOLS/simg2img
    fi

    mkdir -p $TOP/out/host/linux-x86/bin
    cp $SCRIPTS_DIR/tools/mkuserimg.sh $TOP/out/host/linux-x86/bin/mkuserimg.sh
    cp $SCRIPTS_DIR/tools/make_ext4fs $TOP/out/host/linux-x86/bin/make_ext4fs
    cp $SCRIPTS_DIR/tools/zipalign $TOP/out/host/linux-x86/bin/zipalign
    chmod 755 $TOP/out/host/linux-x86/bin/mkuserimg.sh
    chmod 755 $TOP/out/host/linux-x86/bin/make_ext4fs
    chmod 755 $TOP/out/host/linux-x86/bin/zipalign
}

function prepare_system_folder {
    #mount the system image, and change file owner and group to current user, remove lost+found folder
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    local origin_system_image=$1
    local dest_path=$2
    local dest_raw_path=$3
    local dest_raw_file=$1.raw
    local suffix
    local mygroup
    local yimage_size

    if [ -a $dest_raw_file ] ; then
        rm -f $dest_faw_file
    fi

    set -x
    mkdir -p $dest_path
    if [ -f $origin_system_image ] ; then
        suffix=${origin_system_image##*.}
        #if the system image is ext4 mbn file, not compressed
        if [ "$suffix" == "mbn" ] || [ "$suffix" == "img" ] ; then
            $JRD_TOOLS_SIMG2IMG $origin_system_image $dest_raw_file
        #if the system image is compressed zip file
        elif [ "$suffix" == "zip" ] ; then
            ziped_file=$(unzip -l $origin_system_image | grep raw | awk '{print $4}')
            dest_raw_file=$dest_raw_path/$ziped_file
            unzip -o -q $origin_system_image -d $dest_raw_path
        #if the format of system image is not the both above, then exit
        else
            echo "The format of origin system image is incorrect."
            exit 1
        fi
        mount_system_image $dest_raw_file $dest_path
        yimage_size=$(du -b $dest_raw_file | awk '{print $1}')
        rm -f $dest_raw_file
        if [ -n "$SYSTEM_SIZE" -a "$yimage_size" != "$SYSTEM_SIZE" ] ; then
            generate_system_image
            $JRD_TOOLS_SIMG2IMG $PRODUCT_OUT/system.img $dest_raw_file
            rm -f $PRODUCT_OUT/system.img
            umount_system_image $JRD_OUT_SYSTEM
            mount_system_image $dest_raw_file $dest_path
            rm -f $dest_raw_file
        fi
    else
        echo "Can't find origin system image. exit now ... "
        exit 1
    fi
    set +x
    trap - ERR
}

function prepare_userdata_folder {
    #mount the userdata image, and change file owner and group to current user, remove lost+found folder
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    local origin_userdata_image=$1
    local dest_path=$2
    local dest_raw_path=$3
    local dest_raw_file=$1.raw
    local suffix
    local mygroup

    if [ -a $dest_raw_file ] ; then
        rm -f $dest_raw_file
    fi

    set -x
    mkdir -p $dest_path
    if [ -f $origin_userdata_image ] ; then
        suffix=${origin_userdata_image##*.}
        #if the system image is ext4 mbn file, not compressed
        if [ "$suffix" == "mbn" ] || [ "$suffix" == "img" ] ; then
            $JRD_TOOLS_SIMG2IMG $origin_userdata_image $dest_raw_file
        #if the format of system image is not the ext4 mbn file, then exit
        else
            echo "The format of origin system image is incorrect."
            exit 1
        fi
        #mount the userdebug image
        sudo mount -o loop $dest_raw_file $dest_path
        if [ $? -eq 0 ] ; then
            echo "mount $dest_raw_file succeed"
        else
            echo "mount $dest_raw_file failed"
            exit 1
        fi
        #get the name of current user group
        mygroup=$(echo $(groups) | awk '{print $1}')
        #change file owner and group to current user
        sudo chown -hR $USER:$mygroup $dest_path
        #remove lost+found folder
        if [ -d "$dest_path/lost+found" ] ; then
            rm -rf $dest_path/lost+found
        fi
        rm -f $dest_raw_file
    else
        echo "Can't find origin userdata image. exit now ... "
        exit 1
    fi
    set +x
    trap - ERR
}

function prepare_selinux_tag {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    local origin_root_image=$1
    local dest_path=$2
    if [ -f $origin_root_image ] ; then
        mkdir -p $dest_path
        pushd $dest_path > /dev/null
        gunzip -c $origin_root_image | cpio -i
        popd > /dev/null
    fi
    trap - ERR
}

function generate_system_image {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    echo "Now start to generate system image ... "
    PATH=$PATH:$TOP/out/host/linux-x86/bin
    local system_image_size
    if [ -z "$SYSTEM_SIZE" ] ; then
        system_image_size=$(get_build_var BOARD_SYSTEMIMAGE_PARTITION_SIZE)
    else
        system_image_size=$SYSTEM_SIZE
    fi
    local extra_config=""
    if [ -f "$TARGET_ROOT_OUT/file_contexts" ] ; then
        extra_config="$TARGET_ROOT_OUT/file_contexts"
    fi
    echo "mkuserimg.sh -s $JRD_OUT_SYSTEM $PRODUCT_OUT/system.img ext4 system $system_image_size $extra_config"
    mkuserimg.sh -s $JRD_OUT_SYSTEM $PRODUCT_OUT/system.img ext4 system $system_image_size $extra_config
    if [ $? -ne 0 ] ; then
        echo "make system image failed, now exiting ..."
        exit
    fi
    trap - ERR
}

function clean_intermediates_folder {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    pushd $TOP > /dev/null
    while true
    do
        if [ -d $1 ] ; then
            rm -rf $1
        else
            echo "$1 not exist"
        fi

        if [[ "$#" -gt 0 ]] ; then
            # creat this folder for future using
            mkdir -p $1
            shift
        else
            break
        fi
    done
    popd > /dev/null
    trap - ERR
}

function clean_build_logs {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    while true
    do
        if [[ "$#" -gt 0 ]] ; then
            if [ -f $1 ] ; then
                rm -f $1
            fi
            shift
        else
            break
        fi
    done
    trap - ERR
}

function clean_intermediates_files {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    pushd $TOP > /dev/null
    if [ -d $1 ] ; then
        echo "##$1##"
        find $1 -type f | while read -r line
        do
            rm -f $line
        done
    else
        echo "$1 not exist"
    fi
    popd > /dev/null
    trap - ERR
}

function find_res_dir {
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    local my_strings_dir
    local my_icons_dir
    local my_plffile_dir
    #TODO: read string_res.ini file and find out all packages that need to be overlayed
    #      this may missing some important packages that not list in this file,
    MY_RES_DIR=''

    pushd $TOP > /dev/null

    if [ -f $1 ] ; then
        my_strings_dir=$(cat $1 | grep -o -e '^[^\#].*res' | sed 's/\.\///g')
    fi
    if ( $TARGET_BUILD_CUSTOM_IMAGES ) ; then
        my_icons_dir=$(unzip -l $JRD_WIMDATA/wcustores/Photos/$TARGET_PRODUCT/images.zip | grep -E "png|jpg" | awk '{print $4}' | sed 's:res.*:res:')
    fi
    my_plffile_dir=$(for path in ${MY_PLF_FILE_FOLDER[@]}; do find $path -type f -name *.plf | sed 's:isdm.*plf:res:';done)

    MY_RES_DIR=$(echo "$my_strings_dir $my_icons_dir $my_plffile_dir" | sed 's:\s:\n:g' | sort | uniq)

    popd > /dev/null

    if [ -n "$MY_RES_DIR" ] ; then
        echo "MY_RES_DIR=$MY_RES_DIR"
    else
        echo "Can't get res dir list, exit now ... "
        exit -1
    fi
    trap - ERR
}

function collect_build_info()
{
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    set -x
    bash $SCRIPTS_DIR/tools/check_perso.sh -t $TOP -p "$TARGET_PRODUCT" -b "$Branch"
    if [ -f "results.xml" ]; then
        python $SCRIPTS_DIR/tools/insert_build_info.py results.xml
        rm results.xml
    fi
    set +x
    trap - ERR
}



while getopts p:t:s:y:u:z:d:m:v: o
do
    case "$o" in
    p) TARGET_PRODUCT="$OPTARG";;
    t) TOP="$OPTARG";;
    s) ORIGIN_SYSTEM_IMAGE="$OPTARG";;
    y) SYSTEM_SIZE="$OPTARG";;
    u) ORIGIN_USERDATA_IMAGE="$OPTARG";;
    z) USERDATA_SIZE="$OPTARG";;
    m) TARGET_THEME="$OPTARG";;
    v) PERSO_VERSION="$OPTARG";;
    d) DEBUG_ONLY="$OPTARG";;
    [?]) usage ;;
    esac
done

if [ -z "$TARGET_PRODUCT" ]; then
    echo "Please specify target product."
    usage
fi

if [ -z "$TOP" ]; then
    echo "Please specify TOP folder."
    usage
else
    TOP=$(readlink -e $TOP)
fi

if [ -z "$ORIGIN_SYSTEM_IMAGE" ] ; then
    echo "Please specify where to find ORIGIN_SYSTEM_IMAGE."
    usage
elif [ -f "$ORIGIN_SYSTEM_IMAGE" ] ; then
    ORIGIN_SYSTEM_IMAGE=$(readlink -e $ORIGIN_SYSTEM_IMAGE)
    echo "ORIGIN_SYSTEM_IMAGE=$ORIGIN_SYSTEM_IMAGE"
fi

if [ -z "$ORIGIN_USERDATA_IMAGE" ] ; then
    echo "Please specify where to find ORIGIN_USERDATA_IMAGE."
    usage
elif [ -f "$ORIGIN_USERDATA_IMAGE" ] ; then
    ORIGIN_USERDATA_IMAGE=$(readlink -e $ORIGIN_USERDATA_IMAGE)
    echo "ORIGIN_USERDATA_IMAGE=$ORIGIN_USERDATA_IMAGE"
fi

if [ -z "$TARGET_THEME" ] ; then
    echo "Please specify TARGET_THEME type."
    usage
else
    echo "TARGET_THEME=$TARGET_THEME"
fi

if [ -z "$PERSO_VERSION" ] ; then
    echo "Please specify PERSO version."
    usage
else
    echo "PERSO_VERSION=$PERSO_VERSION"
    MAIN_VERSION=v${PERSO_VERSION:1:3}${PERSO_VERSION:6:1}
    Branch=$(ls $TOP/manifests/ver/$TARGET_PRODUCT/ | grep "0.xml" | grep -o "^${TARGET_PRODUCT}_.*_${MAIN_VERSION}" | sed -e 's/'$TARGET_PRODUCT'_//' -e 's/_'$MAIN_VERSION'//')
fi

ORIGIN_ROOT_IMAGE=$(dirname $ORIGIN_SYSTEM_IMAGE)/ramdisk.img
ORIGIN_PERSO_TAR=$TOP/perso.tar.gz
if [ ! -f "$ORIGIN_PERSO_TAR" ] ; then
    if [ -f "$(dirname $ORIGIN_SYSTEM_IMAGE)/perso.tar.gz" ] ; then
        mv $(dirname $ORIGIN_SYSTEM_IMAGE)/perso.tar.gz $ORIGIN_PERSO_TAR
    fi
fi

SCRIPTS_DIR=$(dirname $0)

#indicate the fold of wimdata in the source code
JRD_WIMDATA=$TOP/jb_wimdata_ng
#indicate the path of the jrd tools
JRD_TOOLS=$TOP/device/tct/common/perso/tools
#indicate the arct
JRD_TOOLS_ARCT=$JRD_TOOLS/arct/prebuilt/arct
#indicate the simg2img tool
JRD_TOOLS_SIMG2IMG=$JRD_TOOLS/simg2img
#indicate the main path for the build system of jrdcom
JRD_BUILD_PATH=$TOP/device/tct
#indicate the main path for the build system of a certain project
JRD_BUILD_PATH_DEVICE=$JRD_BUILD_PATH/$TARGET_PRODUCT
#the path of the system properties plf
JRD_PROPERTIES_PLF=$TOP/device/tct/$TARGET_PRODUCT/perso/isdm_sys_properties.plf
#the audio param path
JRD_PROPERTIES_AUDIO=$TOP/vendor/qcom/proprietary/mm-audio/audcal/family-b/acdbdata/8916/$TARGET_PRODUCT
JRD_PROPERTIES_AUDIO_SmartPA=$TOP/hardware/qcom/audio/tfa9897/settings
AUDIO_EFFECT_PATH=$TOP/vendor/tct/source/apps/JrdAudioEffect/$TARGET_PRODUCT
#indicate the jrd custom resource path in /out
JRD_CUSTOM_RES=$TOP/out/target/perso/$TARGET_PRODUCT/jrdResAssetsCust
#indicate the product out path
PRODUCT_OUT=$TOP/out/target/product/$TARGET_PRODUCT
#indicate the custpack path
JRD_OUT_CUSTPACK=$PRODUCT_OUT/system/custpack

TARGET_ROOT_OUT=$PRODUCT_OUT/root
TARBALL_OUT_DIR=$PRODUCT_OUT/tarball
JRD_OUT_SYSTEM=$PRODUCT_OUT/system
JRD_OUT_USERDATA=$PRODUCT_OUT/data

THEME_RESOUCE_PATH=$JRD_WIMDATA/wcustores/theme/output_zip/$TARGET_THEME
THEME_OUT_PATH=$PRODUCT_OUT/system
#the path of overlay apk
TARGET_OUT_VENDOR_OVERLAY=$PRODUCT_OUT/system/vendor/overlay

MY_ANDROID_JAR_TOOL=$TOP/prebuilts/sdk/current/android.jar
MY_AAPT_TOOL=$TOP/prebuilts/sdk/tools/linux/aapt
#the path of gen tarball scripts
AUTO_SCRIPTS_DIR=$TOP/vendor/tct/source/qcn/auto_make_tar

TARGET_OUT_APP_PATH="$TOP/$(get_build_var TARGET_OUT_APP_PATH)"

TARGET_OUT_PRIV_APP_PATH="$TOP/$(get_build_var TARGET_OUT_PRIV_APP_PATH)"

TARGET_OUT_JAVA_LIBRARIES="$TOP/$(get_build_var TARGET_OUT_JAVA_LIBRARIES)"

TARGET_OUT_VENDOR_APPS="$TOP/$(get_build_var TARGET_OUT_VENDOR_APPS)"

#get apk list which isdm "JRD_PRODUCT_PACKAGES" value is set to "0" in isdm_sys_properties.plf
JRD_PRODUCT_PACKAGES=$(get_build_var "JRD_PRODUCT_PACKAGES")
if [ -f "$JRD_WIMDATA/wcustores/gms_apk_unselected.txt" ] && [ ! "${PERSO_VERSION:4:2}" == "ZZ" ]; then
    JRD_GOOLGE_PACKAGES=($(cat "$JRD_WIMDATA/wcustores/gms_apk_unselected.txt"))
    JRD_PRODUCT_PACKAGES=(${JRD_PRODUCT_PACKAGES[@]} ${JRD_GOOLGE_PACKAGES[@]})
fi
#plf file search path
MY_PLF_FILE_FOLDER=(frameworks/base/core
                    frameworks/base/packages
                    packages/apps
                    packages/providers
                    packages/services
                    packages/inputmethods
                    vendor/qcom/proprietary/telephony-apps
                    vendor/tct/source/apps
                    vendor/tct/source/frameworks
                    vendor/tctalone/apps
                    vendor/tctalone/TctAppPackage )


if [ -z "$DEBUG_ONLY" ] ; then
    umount_system_image $JRD_OUT_SYSTEM
    umount_system_image $JRD_OUT_USERDATA
    clean_intermediates_folder $TOP/out
    clean_build_logs "remove_apks.log" "missing_package.log" "ungene_package.log" "overlay-failed.log" "sign-failed.log" "read_variable_error.log"
    prepare_tools
    if [ -f "$ORIGIN_PERSO_TAR" ] ; then
        pushd $TOP > /dev/null
        tar xvzf perso.tar.gz
        popd > /dev/null
    else
        if [ -f "$ORIGIN_SYSTEM_IMAGE" -a -f "$ORIGIN_USERDATA_IMAGE" -a -f "$ORIGIN_ROOT_IMAGE" ] ; then
            prepare_system_folder $ORIGIN_SYSTEM_IMAGE $JRD_OUT_SYSTEM $PRODUCT_OUT
            prepare_userdata_folder $ORIGIN_USERDATA_IMAGE $JRD_OUT_USERDATA $PRODUCT_OUT
            prepare_selinux_tag $ORIGIN_ROOT_IMAGE $TARGET_ROOT_OUT
        else
            echo "ERROR: Important image missing..."
            exit
        fi
    fi
fi

generate_userdata_image
umount_system_image $JRD_OUT_USERDATA

prepare_overlay_res
prepare_audio_param
remove_extra_apk
generate_overlay_packages
change_system_ver
prepare_3rd_party_apk
prepare_gid_config
release_key
prepare_device_config_xml
check_whitespace
generate_system_image
generate_tarball
generate_splash_image
collect_build_info
umount_system_image $JRD_OUT_SYSTEM
echo "Finished build customization package."
