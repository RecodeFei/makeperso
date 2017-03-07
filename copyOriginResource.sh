#!/bin/bash
#add by feikuang@tcl.com for defect 1505571
#[SWD-Test][CTS]android.print.cts.PrintDocumentAdapterContractTest
keyXmls=(donottranslate-cldr.xml donottranslate.xml)
JRD_WIMDATA=$1
MY_RES_DIR=$2
TOP=$3
JRD_CUSTOM_RES=$4
    trap 'traperror ${LINENO} ${FUNCNAME} ${BASH_LINENO}' ERR
    echo "now copy origin resource"
    local_config=$JRD_WIMDATA/wlanguage/src/local.config
    entrylocal=`cat $local_config | grep "^[^#]" | cut -d ',' -f3 | sed 's/[[:space:]]//g'`
    for modulePath in $MY_RES_DIR
    do
        echo "modulePath=$modulePath"
        if [ -d "$TOP/$modulePath" ]; then
        mkdir -p $JRD_CUSTOM_RES/$modulePath
        #allValues=`find $TOP/$modulePath -type d -name "values-*"`
        for keyXml in ${keyXmls[@]}
        do
           if [ -f "$TOP/$modulePath/values/$keyXml" ]; then
           mkdir -p $JRD_CUSTOM_RES/$modulePath/values
           cp -f $TOP/$modulePath/values/$keyXml $JRD_CUSTOM_RES/$modulePath/values/$keyXml
           fi
           for entryValue in $entrylocal
           do
                if [ -f "$TOP/$modulePath/values-$entryValue/$keyXml" ]; then
                mkdir -p $JRD_CUSTOM_RES/$modulePath/values-$entryValue
                cp -f $TOP/$modulePath/values-$entryValue/$keyXml $JRD_CUSTOM_RES/$modulePath/values-$entryValue/$keyXml
                fi
           done
        done
        fi

    done
    trap - ERR
