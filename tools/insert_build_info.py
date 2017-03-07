#!/bin/env python
#
#   usage:  python insert_info_test.py   result.xml
#
#   result.xml is the output file from check_perso.sh
#
#   This script used to insert all build information to database
#   Author:  DingYanghuang
#   Date:    2015-8-26

import xml.dom.minidom
import sys
import mydb
import MySQLdb

def usage():
    print '''
#   usage:  python insert_info_test.py   result.xml#

#   result.xml is the output file from check_perso.sh#
#   This script used to insert all build information to database
    '''

def getFeatures(dom):
    features = []
    nodes = dom.getElementsByTagName("feature")
    for node in nodes:
        if node.hasAttribute("name"):
            features.append(node.getAttribute("name"))

    return features

def getApks(dom):
    apks = []
    nodes = dom.getElementsByTagName("apk")
    for node in nodes:
        apks.append(dict(name=node.getAttribute('name'), version=node.getAttribute('version'), package=node.getAttribute('package')))

    return apks

def getProp(dom, prop):
    '''
    <project name="m823_orange"/>
    <main name="3C1K"/>
    <perso name="CK4"/>
    <model name="M823F"/>
    <branch name="l8936_orange"/>
    <builddate name="2015-07-17 17:14:40"/>
    <fingerprint name="TCL/m823_orange/m823_orange:5.0.2/LRX22G/v3C1K-0:user/release-keys"/>
    <abi name="arm64-v8a"/>
    <author name="Fan Yi"/>
    <androidver name="5.0.2"/ '''

    node = dom.getElementsByTagName(prop)[0]
    return node.getAttribute('name')



def main():
    dom = xml.dom.minidom.parse(sys.argv[1])
    features = getFeatures(dom)
    apks = getApks(dom)
    project = getProp(dom, 'project')
    mainVer = getProp(dom, 'main')
    persoVer= getProp(dom, 'perso')
    model   = getProp(dom, 'model')
    branch  = getProp(dom, 'branch')
    builddate   = getProp(dom, 'builddate')
    fingerprint = getProp(dom, 'fingerprint')
    abi     = getProp(dom, 'abi')
    author  = getProp(dom, 'author')
    androidver = getProp(dom, 'androidver')
    efuse = getProp(dom, 'efuse')
    simlock = getProp(dom, 'simlock')
    kernelconfig = getProp(dom, 'kernelconfig')
    platform   = getProp(dom, 'platform').upper()
    platform_code=getProp(dom, 'platform_code')

    #print features

    db = mydb.MYDB()
    try:
        # insert platform information if not exist in db;
        ret = db.executeAndFetch("select pt_nam \
                                  from int_platform \
                                  where pt_nam='%s';" \
                                  % platform)
        if not ret:
            db.executeAndCommit("INSERT int_platform \
                                (pt_nam, pt_desc) \
                                value('%s', '%s');" \
                                % (platform, "QCT platform " + platform))

        # insert project information if not exist in db;
        ret = db.executeAndFetch("select prj_name \
                                    from int_projects \
                                    where prj_name='%s';" \
                                    % project)
        if not ret:
            db.executeAndCommit("INSERT int_projects \
                                (prj_name, prj_ftp_nam, prj_last_doc_num, prj_pt_code, prj_platform) \
                                value('%s', '%s', %d, '%s', '%s');" \
                                % (project, project, 0, platform_code, platform))

        # check the new version record already record or not
        ret = db.executeAndFetch("select ver_main,ver_perso,ver_builddate \
                                    from int_versions \
                                    where ver_project='%s' and ver_main='%s' and ver_perso='%s';" \
                                    % (project, mainVer, persoVer))
        print "Insert new record: \nProject name =\t%s\nMain ver =\t%s\nPerso ver =\t%s\n" \
                            % (project, mainVer, persoVer)

        # rename the main version if duplication main version found
        if ret:
            date=ret[0][2]
            newMainVer=mainVer + '-' + date.isoformat()
            db.execute("update int_versions \
                        set ver_main='%s' \
                        where ver_main='%s' and ver_project='%s' and ver_perso='%s';" \
                        % (newMainVer, mainVer, project, persoVer))

        # insert new version
        cmd = "INSERT int_versions \
                (ver_project, ver_main, ver_perso, ver_model, ver_branch, ver_builddate, \
                ver_fingerprint, ver_abi, ver_author, ver_android, ver_efused, ver_simlock, ver_defconfig, ver_feature_list, ver_apk_list, \
                ver_cts_approved, ver_feature_approved, ver_apk_approved) \
                value('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', \"%s\", \"%s\", '%s', '%s', '%s');" \
                % (project, mainVer, persoVer, model, branch, builddate, \
                fingerprint, abi, author, androidver, efuse, simlock, kernelconfig, features, apks, \
                'N', 'N', 'N')

        db.executeAndCommit(cmd)

    except MySQLdb.Error, e:
        try:
            print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
        except IndexError:
            print "MySQL Error: %s" % str(e)
        exit(1)




if __name__ == '__main__':
    if len(sys.argv) < 2:
        usage()
        exit(1)

    main()

