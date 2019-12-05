#!/usr/bin/python3.7
import os
import sys, getopt
import string
import re
import errno
from urllib.request import urlopen
from urllib.error import HTTPError
from bs4 import BeautifulSoup

failed_automation  = []
failed_product     = []
failed_environment = []
failed_cancelled   = []
failed_in_progress = []
failed_pending     = []
passed_fully       = []
passed_softfailed  = []
openqa_url_prefix = "https://openqa.opensuse.org"
openqa_log_filename  = "/home/openqa_review/autoinst_temp.txt"
openqa_review_path      = "/home/openqa_review"
openqa_review_status = ''
openqa_testsuites_num = 0

def openqa_review_result(distri, version, build, groupid, arch):
    openqa_url_addr = "%s/tests/overview?distri=%s&version=%s&build=%s&groupid=%s" % (openqa_url_prefix,distri,version,build,groupid)
    print (openqa_url_addr)

    try:
        os.makedirs(openqa_review_path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    try:
        openqa_html_page = urlopen(openqa_url_addr)
    except HTTPError as e:
        print (e)
    if openqa_html_page is None:
        print ("URL is not found\n")
    else:
        openqa_bsObj = BeautifulSoup(openqa_html_page, 'lxml')
        for alltds in openqa_bsObj.findAll("td"):
            if 'id' in alltds.attrs:
                print (alltds.attrs['id'])
                testsuite_name = alltds.attrs['id']
                if re.match(r".*%s" % arch, testsuite_name):
                    for allis in alltds.findAll("i", {"class":re.compile("status*")}):
                        if 'title' in allis.attrs:
                            testsuite_status = allis.attrs['title']
                            print (testsuite_status)
                            if re.match("Done: failed", testsuite_status):
                                testsuite_triplet = [testsuite_name, '', '']    
                                for allas in alltds.findAll("a", {"class":"failedmodule"}):
                                    if 'data-async' in allas.attrs:
                                        testsuite_failedmodule = allas.attrs['data-async'].split('/')[-2]
                                        print (testsuite_failedmodule)
                                        testsuite_triplet[1] = testsuite_failedmodule
                                i_test_label_exist = 0
                                i_test_label_comment = 0
                                for allis in alltds.findAll("i", {"class":re.compile("test-label*")}):
                                    if 'title' in allis.attrs:
                                        i_test_label_exist = 1
                                        testsuite_reference = allis.attrs['title']
                                        if re.match(".*Bug referenced: bsc#*", testsuite_reference) or re.match(".*Bug referenced: poo#*", testsuite_reference) or re.match("Bug referenced: gh#.*", testsuite_reference):
                                            testsuite_triplet[2] = testsuite_triplet[2] + testsuite_reference
                                        if re.match(".*comment available*", testsuite_reference):
                                            i_test_label_comment = 1
                                            testsuite_comment_url  = openqa_url_prefix + allis.parent.attrs['href']
                                            testsuite_comment_html = urlopen(testsuite_comment_url)
                                            testsuite_comment      = BeautifulSoup(testsuite_comment_html, 'lxml')
                                            for alldivs in testsuite_comment.findAll("div", {"class":"media-comment markdown"}):
                                                for allps in alldivs.findAll("p"):
                                                    testsuite_reference  = allps.get_text()
                                                    testsuite_triplet[2] = testsuite_triplet[2] + testsuite_reference
                                if i_test_label_exist == 1:
                                        if re.match(".*Bug referenced: bsc#*", testsuite_triplet[2]):
                                            failed_product.append(testsuite_triplet)
                                            break
                                        elif re.match(".*Bug referenced: poo#*", testsuite_triplet[2]) or re.match("Bug referenced: gh#.*", testsuite_triplet[2]):
                                            failed_automation.append(testsuite_triplet)
                                            break
                                        elif i_test_label_comment == 1:
                                            failed_environment.append(testsuite_triplet)
                                        else:
                                            testsuite_triplet[2] = 'Pending for review'
                                            failed_pending.append(testsuite_triplet)
                                else:
                                    a_href_test_needle = 0
                                    a_href_test_exception = 0
                                    for allas in alltds.findAll("a", {"href":re.compile("/tests/[0-9]+$")}):
                                        testsuite_url      = openqa_url_prefix + allas.attrs['href'] + '/file/autoinst-log.txt'
                                        try:
                                            testsuite_html = urlopen(testsuite_url)
                                        except HTTPError as e:
                                            print (e)
                                            a_href_test_exception = 1
                                            testsuite_triplet[2] = 'autoinst log is not available. Need further review'
                                            failed_pending.append(testsuite_triplet)
                                            break
                                        else:
                                            testsuite_log      = BeautifulSoup(testsuite_html, 'lxml').get_text()
                                            testsuite_log_file = open(openqa_log_filename, 'w')
                                            testsuite_log_file.write(testsuite_log)
                                            testsuite_log_file.close()
                                            testsuite_log_file = open(openqa_log_filename, 'r')
                                            for myline in testsuite_log_file:
                                                if re.match("^.*no candidate needle with tag*", myline):
                                                    a_href_test_needle = 1
                                                    testsuite_triplet[2] = testsuite_triplet[2] + myline
                                            testsuite_log_file.close()
                                    if (a_href_test_needle == 1 and a_href_test_exception == 0):
                                        failed_automation.append(testsuite_triplet)
                                        break
                                    elif (a_href_test_exception == 0 and a_href_test_needle == 0):
                                        a_failed_module_bug = 0
                                        for allas in alltds.findAll("a", {"class":"failedmodule"}):
                                            testsuite_failedmodule = allas.get_text()
                                            print (testsuite_failedmodule)
                                            if re.match(".*hotplug*", testsuite_failedmodule, re.I) or re.match(".*virsh_external_snapshot*", testsuite_failedmodule, re.I) or re.match(".*virsh_internal_snapshot*", testsuite_failedmodule, re.I) or re.match(".*guest_installation*", testsuite_failedmodule, re.I) or re.match(".*guest_upgrade*", testsuite_failedmodule, re.I) or re.match(".*host_upgrade_step*", testsuite_failedmodule, re.I) or re.match(".*guest_migration*", testsuite_failedmodule, re.I) or re.match(".*pvusb_run*", testsuite_failedmodule, re.I):
                                                a_failed_module_bug = 1
                                                testsuite_triplet[2] = 'Product bug to be opened (Only Suggestion. Need further review.)'
                                                break
                                        if a_failed_module_bug == 1:
                                            failed_product.append(testsuite_triplet)
                                            break
                                        else:
                                            testsuite_triplet[2] = 'Pending for review'
                                            failed_pending.append(testsuite_triplet)
                                            break
                            if re.match(".*incomplete*", testsuite_status):
                                testsuite_triplet = [testsuite_name, '', '']
                                i_test_label_exist = 0
                                for allis in alltds.findAll("i", {"class":re.compile("test-label*")}):
                                    if 'title' in allis.attrs:
                                        i_test_label_exist = 1
                                        testsuite_reference = allis.attrs['title']
                                        if re.match(".*Bug referenced: poo#*", testsuite_reference):
                                            testsuite_triplet[2] = testsuite_reference
                                            failed_automation.append(testsuite_triplet)
                                            break
                                        elif re.match("Bug referenced: gh#.*", testsuite_reference):
                                            testsuite_triplet[2] = testsuite_reference
                                            failed_automation.append(testsuite_triplet)
                                            break
                                        elif re.match(".*comment available*", testsuite_reference):
                                            testsuite_comment_url  = openqa_url_prefix + allis.parent.attrs['href']
                                            testsuite_comment_html = urlopen(testsuite_comment_url)
                                            testsuite_comment      = BeautifulSoup(testsuite_comment_html, 'lxml')
                                            for alldivs in testsuite_comment.findAll("div", {"class":"media-comment markdown"}):
                                                for allps in alldivs.findAll("p"):
                                                    testsuite_reference  = allps.get_text()
                                                    testsuite_triplet[2] = testsuite_triplet[2] + testsuite_reference
                                            failed_environment.append(testsuite_triplet)
                                            break
                                        else:
                                            testsuite_triplet[2] = 'Incomplete might be caused by environment or automation issue. Need further review'
                                            failed_pending.append(testsuite_triplet)
                                            break
                                if i_test_label_exist == 1:
                                    break
                                else:
                                    testsuite_triplet = [testsuite_name, '', 'Incomplete might be caused by environment or automation issue. Need further review']
                                    failed_pending.append(testsuite_triplet)
                                    break
                            if re.match("Done: parallel_failed", testsuite_status):
                                testsuite_triplet = [testsuite_name, '', 'Pending for review (parallel_failed)']
                                failed_pending.append(testsuite_triplet)
                                break
                            if re.match(".*cancelled*", testsuite_status):
                                failed_cancelled.append(testsuite_name)
                                break
                            if re.match(".*passed*", testsuite_status):
                                passed_fully.append(testsuite_name)
                                break
                            if re.match(".*softfailed*", testsuite_status):
                                passed_softfailed.append(testsuite_name)
                                break
                            if re.match(".*running*", testsuite_status) or re.match(".*scheduled*", testsuite_status) or re.match(".*uploading*", testsuite_status):
                                failed_in_progress.append(testsuite_name)
                                break

        failed_list_len = len(failed_automation) + len(failed_product) + len(failed_environment) + len(failed_in_progress) + len(failed_pending) + len(failed_cancelled)
        passed_list_len = len(passed_fully) + len(passed_softfailed)
        openqa_testsuites_num = failed_list_len + passed_list_len

        print ("\n\nTest Suites are %d in total\n" % openqa_testsuites_num)
        print ("Failed Test Suites are %d in total (Including all sorts of failure)\n" % failed_list_len)
        print ("Passed Test Suites are %d  in total (Including softfailed)\n" % passed_list_len)

        if (failed_list_len > passed_list_len) or (passed_list_len == 0):
            openqa_review_status = 'RED'
        elif (failed_list_len > 0):
            openqa_review_status = 'AMBER'
        else:
            openqa_review_status = 'GREEN'

        if os.path.exists(openqa_log_filename):
            os.remove(openqa_log_filename)

        with open('/home/openqa_review/openqa_review_result_%s_%s_build%s_%s_%s.txt' % (distri,version,build,groupid,arch), 'w') as filehandler:
            filehandler.write("Build %s\n\n" % build)
            filehandler.write("Arch %s\n\n" % arch)
            filehandler.write("Status %s\n\n" % openqa_review_status)
            filehandler.write("Summary:\n\n")
            ##### Failed by Product Issues ######
            filehandler.write("- Failed by Product Issues (%.1f%%  %d in total):\n\n" % ((100 * len(failed_product) / openqa_testsuites_num), len(failed_product)))
            if len(failed_product) == 0:
                filehandler.write(" - No exhibition till now\n\n") 
            else:
                for mytestsuite in failed_product:
                    filehandler.write(" - %s   %s   %s\n\n" % (mytestsuite[0],mytestsuite[1],mytestsuite[2]))   
            ##### Failed by Automation Issues #####
            filehandler.write("- Failed by Automation Issues (%.1f%%  %d in total):\n\n" % ((100 * len(failed_automation) / openqa_testsuites_num), len(failed_automation)))
            if len(failed_automation) == 0:
                filehandler.write(" - No exhibition till now\n\n") 
            else:
                for mytestsuite in failed_automation:
                    filehandler.write(" - %s   %s   %s\n" % (mytestsuite[0],mytestsuite[1],mytestsuite[2]))   
            ##### Failed by Environment Issues #####
            filehandler.write("- Failed by Environment Issues (%.1f%%  %d in total):\n\n" % ((100 * len(failed_environment) / openqa_testsuites_num), len(failed_environment)))
            if len(failed_environment) == 0:
                filehandler.write(" - No exhibition till now\n\n") 
            else:
                for mytestsuite in failed_environment:
                    filehandler.write(" - %s   %s   %s\n\n" % (mytestsuite[0],mytestsuite[1],mytestsuite[2]))   
            ##### Failed and Pending for Resolution #####
            filehandler.write("- Failed and Pending for Resolution (%.1f%%  %d in total):\n\n" % ((100 * len(failed_pending) / openqa_testsuites_num), len(failed_pending)))
            if len(failed_pending) == 0:
                filehandler.write(" - No exhibition till now\n\n") 
            else:
                for mytestsuite in failed_pending:
                    filehandler.write(" - %s   %s   %s\n\n" % (mytestsuite[0],mytestsuite[1],mytestsuite[2]))   
            ##### Passed #####
            filehandler.write("- Passed (%.1f%%  %d in total):\n\n" % ((100 * len(passed_fully) / openqa_testsuites_num), len(passed_fully)))
            if len(passed_fully) == 0:
                filehandler.write(" - No exhibition till now\n\n") 
            else:
                for mytestsuite in passed_fully:
                    filehandler.write(" - %s\n\n" % mytestsuite)   
            ##### Softfailed #####
            filehandler.write("- Softfailed (%.1f%%  %d in total):\n\n" % ((100 * len(passed_softfailed) / openqa_testsuites_num), len(passed_softfailed)))
            if len(passed_softfailed) == 0:
                filehandler.write(" - No exhibition till now\n\n") 
            else:
                for mytestsuite in passed_softfailed:
                    filehandler.write(" - %s\n\n" % mytestsuite)   
            ##### In Progress #####
            filehandler.write("- In Progress (%.1f%%  %d in total):\n\n" % ((100 * len(failed_in_progress) / openqa_testsuites_num), len(failed_in_progress)))
            if len(failed_in_progress) == 0:
                filehandler.write(" - No exhibition till now\n\n") 
            else:
                for mytestsuite in failed_in_progress:
                    filehandler.write(" - %s\n\n" % mytestsuite)   
            ##### Cancelled #####
            filehandler.write("- Cancelled (%.1f%%  %d in total):\n\n" % ((100 * len(failed_cancelled) / openqa_testsuites_num), len(failed_cancelled)))
            if len(failed_cancelled) == 0:
                filehandler.write(" - No exhibition till now\n\n") 
            else:
                for mytestsuite in failed_cancelled:
                    filehandler.write(" - %s\n\n" % mytestsuite)   
        print ("Please check out review result at /home/openqa_review/openqa_review_result_%s_%s_build%s_%s_%s.txt" % (distri,version,build,groupid,arch)) 
        filehandler.close()

def main(argv):
    distri_str = ''
    version_str = ''
    build_str = ''
    groupid_str = ''
    arch_str = ''
    try:
        opts,args = getopt.getopt(argv,"hd:v:b:g:a:",["help","distri=","version=","build=","groupid=","arch="])
    except getopt.GetoptError:
        print ("openqa-review-result.py -d <distribution> -v <version> -b <buildnumber> -g <groupip> -a <architecture>")
        sys.exit(2)
    for opt,arg in opts:
        if opt in ("-h", "--help"):
           print ("openqa-review-result.py -d <distribution> -v <version> -b <buildnumber> -g <groupip> -a <architecture")
           sys.exit()
        elif opt in ("-d", "--distribution"):
             distri_str = arg
        elif opt in ("-v", "--version"):
             version_str = arg
        elif opt in ("-b", "--build"):
             build_str = arg
        elif opt in ("-g", "--groupip"):
             groupid_str = arg
        elif opt in ("-a", "--arch"):
             arch_str = arg
    print ("Distribution is", distri_str)
    print ("Version is", version_str)
    print ("Build is", build_str)
    print ("Groupid is", groupid_str)
    print ("Arch is", arch_str)
    openqa_review_result(distri_str, version_str, build_str, groupid_str, arch_str)

if __name__ == "__main__":
    main(sys.argv[1:])
