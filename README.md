# openqa-automated-test-result-review
This program gathers test results of openqa automated tests, and sorts all failed tests by their respective failures along with bug references, comments available, specific root causes or suggestions. It also supports post results onto openQA job group webpage automatically by using selenium

# Usage
## v1.0
openqa-review-result.py -d distribution -v version -b buildnumber -g groupip -a architecture
## v2.0
openqa-review-result.py -d distribution -v version -b buildnumber -g groupip -a architecture -s openqa.opensuse.org 
## v3.0
openqa-review-result.py -d distribution -v version -b buildnumber -g groupip -a architecture -s openqa.opensuse.org -p



This program was initially developed for internal openQA. Because the common and identical website structure of openQA tool across sites in different locations and for different purposes, this program should also be effective and helpful. 

For example, openqa.opensuse.org can be accessed from everywhere:

"./openqa-review-result.py -d opensuse -v Tumbleweed -b 20190626 -g 1 -a x86_64 -s openqa.opensuse.org -p" generates review summary for   
https://openqa.opensuse.org/tests/overview?distri=opensuse&version=Tumbleweed&build=20190626&groupid=1 
"./openqa-review-result.py -d microos -v Tumbleweed -b 20190626 -g 1 -a x86_64 -s openqa.opensuse.org -p" generates review summary for
https://openqa.opensuse.org/tests/overview?distri=microos&version=Tumbleweed&build=20190626&groupid=1
## v4.0
Use golang to do SLES builds comparison to achieve faster speed. This golang script is called inside by openqa-review-result.py by using os.system. User can use openqa-review-result.py with "-c" option to use this feature.
  
# Future Development
1. Any more advacned way to incorparate more delicate assortment and findings will be implemented along with the effort spent on generating such review summary and when time permits.
2. Any bug reported and improvement suggested are welcome.
