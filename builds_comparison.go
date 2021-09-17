package main
import (
    "fmt"
    //"io/ioutil"
    "net/http"
    "github.com/PuerkitoBio/goquery"
    "time"
    "strings"
    "os"
    "bufio"
    "log"
    "errors"
    "sync"
    "strconv"
    "regexp"
    //"net/url"
)

var wg sync.WaitGroup

func get_Packages_Listing(repoURL string, comch chan<- string) {

    defer wg.Done()
    funcstart := time.Now()
    var packages_list []string
    httpclient := &http.Client{
        Timeout: 300 * time.Second,
    }
    http_request, http_request_err := http.NewRequest("GET", repoURL, nil)
    check_error(repoURL, http_request_err)

    http_request.Header.Set("pragma", "no-cache")
    http_request.Header.Set("cache-control", "no-cache")
    http_request.Header.Set("dnt", "1")
    http_request.Header.Set("upgrade-insecure-requests", "1")
    http_request.Header.Set("referer", "http://openqa.suse.de")
    http_response, http_response_err := httpclient.Do(http_request)
    check_error(repoURL, http_response_err)

    if http_response.StatusCode == 200 {
        query_doc, query_err := goquery.NewDocumentFromReader(http_response.Body)
        check_error(repoURL, query_err)
	query_doc.Find("a").Each(func(i int, s *goquery.Selection) {
            package_name, _ := s.Attr("href")
	    if strings.Contains(package_name, "rpm") {
                package_name_text := s.Text()
		packages_list = append(packages_list, package_name_text)
	    }
	})
    }
    record_packages_in_file(packages_list, repoURL)
    comch <- fmt.Sprintf("Used %.2fs to get packages listing from %s\n", time.Since(funcstart).Seconds(), repoURL)
}

func check_error(error_object string, error_content error) {
    if error_content != nil {
        fmt.Sprintf("While operating on %s: %v reported", error_object, error_content)
        log.Fatal(error_content)
	panic(error_content)
    }
}

func record_packages_in_file(allpackages []string,  allpackagesURL string) {
    allpackagesURL_name := strings.Replace(allpackagesURL, "/", "_", -1)
    allpackagesURL_name = strings.Replace(allpackagesURL_name, ":", "_", -1)
    allpackagesURL_name = strings.Replace(allpackagesURL_name, ".", "_", -1)
    allpackagesURL_name = "/home/waynechen/openqa_review/packages_listing_" + allpackagesURL_name + ".txt"

    if _, stat_dir_err := os.Stat("/home/waynechen/openqa_review/"); errors.Is(stat_dir_err, os.ErrNotExist) {
        fmt.Println("Folder /home/waynechen/openqa_review/ does not exist. Going to create it.\n")
	mkdir_err := os.MkdirAll("/home/waynechen/openqa_review", 0777)
        check_error("/home/waynechen/openqa_review", mkdir_err)
    } else if errors.Is(stat_dir_err, os.ErrExist) {
        fmt.Println("Folder /home/waynechen/openqa_review/ already exists.\n")
    } else {
        check_error("/home/waynechen/openqa_review", stat_dir_err)
    }

    if _, stat_file_err := os.Stat(allpackagesURL_name); errors.Is(stat_file_err, os.ErrNotExist) {
        fmt.Println(allpackagesURL_name + " does not exist.\n")
    } else if errors.Is(stat_file_err, os.ErrExist) {
        fmt.Println(allpackagesURL_name + " already exist. Going to remove it.\n")
	remove_file_err := os.Remove(allpackagesURL_name)
        check_error(allpackagesURL_name, remove_file_err)
    } else {
        check_error(allpackagesURL_name, stat_file_err)
    }

    fmt.Println("Going to create " + allpackagesURL_name + ".\n")
    f, create_file_err := os.Create(allpackagesURL_name)
    check_error(allpackagesURL_name, create_file_err)
    defer f.Close()

    w := bufio.NewWriter(f)
    var totalbytes int
    for _, line := range allpackages {
        nbytes, write_string_err := w.WriteString(line + "\n")
        check_error(allpackagesURL_name, write_string_err)
        totalbytes += nbytes
    }
    fmt.Printf("Wrote %d bytes into %s\n", totalbytes, allpackagesURL_name)
    w.Flush()
}

func get_current_build_number_from_url(linkURL string) string {
    re := regexp.MustCompile("-Build([0-9|\\.]{1,})-")
    res := re.FindStringSubmatch(linkURL)
    fmt.Println("Current build number is " + res[1])
    return res[1]
}

func heuristic_previous_build_number_discovery(build_url string, build_number string) string {
     return_value := "fault"
     current_build_number, _ := strconv.ParseFloat(build_number, 64)
     current_build_number_str := fmt.Sprintf("%.1f", current_build_number)
     match_result, match_err := regexp.MatchString("\\.0", current_build_number_str)
     check_error(current_build_number_str, match_err)
     if match_result == true {
	 current_build_number_str = strings.Replace(current_build_number_str, ".0", "", -1)
     }
     previous_build_number := current_build_number - 0.1
     for previous_build_number > 0 {
	 previous_build_number_str := fmt.Sprintf("%.1f", previous_build_number)
         match_result, match_err = regexp.MatchString("\\.0", previous_build_number_str)
         check_error(previous_build_number_str, match_err)
	 if match_result == true {
	     previous_build_number_str = strings.Replace(previous_build_number_str, ".0", "", -1)
	 }
	 previous_build_url := strings.Replace(build_url, current_build_number_str, previous_build_number_str, -1)
	 check_url_resp, _ := http.Get(previous_build_url)
	 if check_url_resp.StatusCode == 200 {
	     return_value = previous_build_number_str
             break
	 }else {
	     previous_build_number -= 0.1
	 }
     }
     return return_value
}

func do_packages_comparison(current_build_number string, previous_build_number string, repoURL string, comch chan<- string) {
    compstart := time.Now()
    defer wg.Done()
    repoURL_filename := strings.Replace(repoURL, "/", "_", -1)
    repoURL_filename = strings.Replace(repoURL_filename, ":", "_", -1)
    repoURL_filename = strings.Replace(repoURL_filename, ".", "_", -1)
    repoURL_filename_current := "/home/waynechen/openqa_review/packages_listing_" + repoURL_filename + ".txt"
    repoURL_filename_previous := strings.Replace(repoURL_filename_current, strings.Replace(current_build_number, ".", "_", -1), strings.Replace(previous_build_number, ".", "_", -1), -1)
    read_current_file, read_current_file_err := os.Open(repoURL_filename_current)
    check_error(repoURL_filename_current, read_current_file_err)
    current_file_scanner := bufio.NewScanner(read_current_file)
    current_file_scanner.Split(bufio.ScanLines)
    var current_file_TextLines []string
    for current_file_scanner.Scan() {
       current_file_TextLines = append(current_file_TextLines, current_file_scanner.Text())
    }
    read_current_file.Close()

    read_previous_file, read_previous_file_err := os.Open(repoURL_filename_previous)
    check_error(repoURL_filename_previous, read_previous_file_err)
    previous_file_scanner := bufio.NewScanner(read_previous_file)
    previous_file_scanner.Split(bufio.ScanLines)

    changelog_file := "/home/waynechen/openqa_review/changelog_build" + previous_build_number + "_" + repoURL_filename
    changelog_file = strings.Replace(changelog_file, ".", "_", -1)
    changelog_file = changelog_file + ".txt"
    fmt.Println(changelog_file)
    fmt.Println(changelog_file)
    if _, existing_file_err := os.Stat(changelog_file); errors.Is(existing_file_err, os.ErrNotExist) {
        fmt.Println(changelog_file + " does not exist.\n")
    } else {
        check_error(changelog_file, existing_file_err)
        fmt.Println(changelog_file + " already exists. Going to remove it.\n")
        remove_file_err := os.Remove(changelog_file)
        check_error(changelog_file, remove_file_err)
    }

    fmt.Println("Going to create " + changelog_file + ".\n")
    f, create_file_err := os.Create(changelog_file)
    check_error(changelog_file, create_file_err)
    defer f.Close()

    var totalbytes int
    var previous_packages_left []string
    for previous_file_scanner.Scan() {
        package_full_name := previous_file_scanner.Text()
	re := regexp.MustCompile("((-([0-9|\\.]){1,}){1,}(([0-9|a-z|A-Z|\\.){1,}){0,}(_([0-9|\\.|a-z|A-Z]){0,}){0,}([\\+]{1,}.*){0,}){1,}(noarch|x86_64|aarch64|s390x)\\.rpm")
	//re := regexp.MustCompile("(-([0-9|\\.]){1,}){1,2}(noarch|x86_64|aarch64|s390x)\\.rpm")
        package_name := re.ReplaceAllString(package_full_name, "")
        re = regexp.MustCompile("((-([0-9|\\.]){1,}){1,}(([0-9|a-z|A-Z|\\.){1,}){0,}(_([0-9|\\.|a-z|A-Z]){0,}){0,}([\\+]{1,}.*){0,}){1,}")
	//re = regexp.MustCompile("(-([0-9|\\.]){1,}){1,2}")
        package_versions := re.FindStringSubmatch(package_full_name)
	package_version := package_versions[0]
	re = regexp.MustCompile("(noarch|x86_64|aarch64|s390x)\\.rpm")
	package_version = re.ReplaceAllString(package_version, "")
	found_package := "false"
	var current_index int
	var current_line string
	for current_index, current_line = range current_file_TextLines {
	    re := regexp.MustCompile("((-([0-9|\\.]){1,}){1,}(([0-9|a-z|A-Z|\\.){1,}){0,}(_([0-9|\\.|a-z|A-Z]){0,}){0,}([\\+]{1,}.*){0,}){1,}(noarch|x86_64|aarch64|s390x)\\.rpm")
            //re := regexp.MustCompile("(-([0-9|\\.]){1,}){1,2}(noarch|x86_64|aarch64|s390x)\\.rpm")
            current_package_name := re.ReplaceAllString(current_line, "")
            re = regexp.MustCompile("((-([0-9|\\.]){1,}){1,}(([0-9|a-z|A-Z|\\.){1,}){0,}(_([0-9|\\.|a-z|A-Z]){0,}){0,}([\\+]{1,}.*){0,}){1,}")
	    //re = regexp.MustCompile("(-([0-9|\\.]){1,}){1,2}")
            current_package_versions := re.FindStringSubmatch(current_line)
	    current_package_version := current_package_versions[0]
	    re = regexp.MustCompile("(noarch|x86_64|aarch64|s390x)\\.rpm")
	    current_package_version = re.ReplaceAllString(current_package_version, "")
	    if package_name == current_package_name {
		found_package = "true"
		if package_version != current_package_version {
	            //fmt.Println("Package " + package_name + " version changed fom " + package_version + " to " + current_package_version + "\n")
	            w := bufio.NewWriter(f)
                    nbytes, write_string_err := w.WriteString(package_name + " " + package_version + "->" + current_package_version + "\n")
                    check_error(changelog_file, write_string_err)
                    totalbytes += nbytes
                    w.Flush()
	        }
	        //fmt.Println("Package " + package_name + " version stays at " + package_version + "\n")
                break
	    }
        }
	if found_package == "true" {
            if len(current_file_TextLines) == 1 {
                current_file_TextLines = []string{}
            }else if current_index == 0 {
                current_file_TextLines = current_file_TextLines[1:]
            }else if len(current_file_TextLines) - current_index - 1 == 0 {
                if len(current_file_TextLines) > 2 {
                    current_file_TextLines = current_file_TextLines[:current_index-1]
                }else {
                    current_file_TextLines = []string{current_file_TextLines[0]}
                }
            }else if current_index == 1 {
                    current_file_TextLines = append(current_file_TextLines[2:], current_file_TextLines[0])
            }else if current_index == len(current_file_TextLines) - 2 {
                current_file_TextLines = append(current_file_TextLines[:current_index-1], current_file_TextLines[len(current_file_TextLines)-1])
            }else {
                current_file_TextLines = append(current_file_TextLines[:current_index-1], current_file_TextLines[current_index+1:]...)
            }
        }else {
            previous_packages_left = append(previous_packages_left, package_full_name)
	}
    }
    read_previous_file.Close()

    if len(current_file_TextLines) > 0 {
	for _, current_line := range current_file_TextLines {
            w := bufio.NewWriter(f)
            nbytes, write_string_err := w.WriteString("New " +  current_line + "\n")
            check_error(changelog_file, write_string_err)
            totalbytes += nbytes
            w.Flush()
	}
    }
    if len(previous_packages_left) > 0 {
	for _, current_line := range previous_packages_left {
            w := bufio.NewWriter(f)
            nbytes, write_string_err := w.WriteString("Removed " +  current_line + "\n")
            check_error(changelog_file, write_string_err)
            totalbytes += nbytes
            w.Flush()
	}
    }
    comch <- fmt.Sprintf("Used %.2fs to compare and write %d bytes into change log %s\n", time.Since(compstart).Seconds(), totalbytes, changelog_file)
}

func main() {
    mainstart := time.Now()
    comch := make(chan string)
    current_build_number := get_current_build_number_from_url(os.Args[1])
    previous_build_number := heuristic_previous_build_number_discovery(os.Args[1], current_build_number)
    if previous_build_number == "fault" {
        fmt.Println("Failed to get previous build number. Exiting.\n")
	log.Fatal("Program can not continue without build number of the previous build.")
        return
    }
    fmt.Println("Current build number is " + current_build_number + " Previous build number is " + previous_build_number + "\n")
    var previous_repoURLs_list []string
    wg.Add(2 * len(os.Args[1:]))
    for _, repoURL := range os.Args[1:] {
	previous_repoURL := strings.Replace(repoURL, current_build_number, previous_build_number, -1)
        previous_repoURLs_list = append(previous_repoURLs_list, previous_repoURL)
	go get_Packages_Listing(repoURL, comch)
	go get_Packages_Listing(previous_repoURL, comch)
    }
    for range os.Args[1:] {
        fmt.Println(<-comch)
    }
    for range previous_repoURLs_list {
        fmt.Println(<-comch)
    }
    wg.Wait()

    wg.Add(len(os.Args[1:]))
    for _, repoURL := range os.Args[1:] {
	go do_packages_comparison(current_build_number, previous_build_number, repoURL, comch)
    }
    for range os.Args[1:] {
        fmt.Println(<-comch)
    }
    wg.Wait()
    fmt.Printf("%.2fs elapsed in total during getting packages listing and doing comparison.\n", time.Since(mainstart).Seconds())
}

