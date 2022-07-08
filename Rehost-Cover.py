# Rehost Cover Script
# author: hypermodified
# A python script to that will rehost a list of cover urls from random image hosts to ptpimg

# Import dependencies
import os  # Imports functionality that let's you interact with your operating system
import requests  # Imports the ability to make web or api requests
import datetime  # Imports functionality that lets you make timestamps
import ptpimg_uploader  # imports the tool which lets you upload to ptpimg
import config  # imports the config file where you set your API key, directories, etc
from csv import DictReader  # For parsing the input CSV file
from random import randint  # Imports functionality that lets you generate a random number
from time import sleep  # Imports functionality that lets you pause your script for a set period of time
from urllib.parse import urlparse

# Before running this script install the dependencies
# pip install ptpimg_uploader
# pip install pyperclip

# Import directories from config file
list_directory = config.c_list_directory  # imports the directory path to where your albums are
log_directory = config.c_log_directory  # imports the directory path to where you want to write your logs

# Imports site and API information from config file
site_ajax_page = config.c_site_ajax_page  # imports gazelle ajax page
collage_ajax_page = config.c_site_collage_ajax_page  # imports missing cover art collage ajax page
r_api_key = config.c_r_api_key  # imports your RED api key
p_api_key = config.c_p_api_key  # imports your ptpIMG api key
headers = {
    "Authorization": r_api_key,
    "User-Agent": "Rehost-Cover-Script/0.5",
}  # sets the key value pairs for accessing the RED api

# Establishes the counters for completed covers and errors
count = 0
total_count = 0
RED_api_error = 0
ptpimg_api_error = 0
RED_replace_error = 0
cover_missing_error = 0
collage_message = 0
collage_error = 0
error_message = 0
list_error = 0

LOW_QUALITY_HOSTS = {
    "img.photobucket.com",
    "upload.wikimedia.org",
}

BAD_HOSTS = {
    "115.imagebam.com",
}

TRICKY_HOSTS: dict[str, str] = {
    "i.imgur.com": "https://i.imgur.com/removed.png",
    "imgur.com": "https://i.imgur.com/removed.png",
    "tinyimg.io": "https://tinyimg.io/notfound",
}

# A function to log events
def log_outcomes(torrent_id, cover_url, log_name, message):
    global log_directory
    script_name = "Rehost Cover Script"
    log_name = f"{log_name}.txt"
    today = datetime.datetime.now()
    log_path = os.path.join(log_directory, log_name)
    with open(log_path, "a", encoding="utf-8") as log_name:
        log_name.write(f"--{today:%b, %d %Y} at {today:%H:%M:%S} from the {script_name}.\n")
        log_name.write(f"The torrent group {torrent_id} {message}.\n")
        log_name.write(f"Torrent location: https://redacted.ch/torrents.php?id={torrent_id}\n")
        log_name.write(f"Cover location: {cover_url}\n")
        log_name.write(" \n")
        log_name.close()


# A function that writes a summary of what the script did at the end of the process
def summary_text():
    global count
    global total_count
    global list_error
    global RED_replace_error
    global RED_api_error
    global ptpimg_api_error
    global error_message
    global cover_missing_error
    global collage_message
    global collage_error

    print("")
    print(f"This script rehosted {count} album covers out of {total_count} covers.")
    print("")
    if list_error == 0:

        level = "Warning" if RED_replace_error else "Info"
        print(f"--{level}: There were {RED_replace_error} cover urls that failed being added to RED.")

        level = "Warning" if RED_api_error else "Info"
        print(f"--{level}: There were {RED_api_error} covers skipped due to errors with the RED api.")

        level = "Warning" if ptpimg_api_error else "Info"
        print(
            f"--{level}: There were {ptpimg_api_error} covers skipped due to the covers no longer being on the internet or errors with the ptpimg api."
        )

        level = "Warning" if cover_missing_error else "Info"
        print(
            f"--{level}: There were {cover_missing_error} covers skipped due to the covers no longer being on the internet or being a 404 image."
        )

        level = "Warning" if collage_message else "Info"
        print(f"--{level}: There were {collage_message} albums added to a collage due to missing or bad cover art.")

        level = "Warning" if collage_error else "Info"
        print(
            f"--{level}: There were {collage_error} albums that had missing or bad cover art but adding them a collage failed."
        )

        if any(
            [RED_replace_error, RED_api_error, ptpimg_api_error, cover_missing_error, collage_message, collage_error]
        ):
            print("Check the logs to see which torrents and covers had errors and what they were.")
        else:
            print("There were no errors.")

    else:
        print(
            "The was an error loading or parsing the list of torrent ids and cover urls, please check it and try again."
        )


# A function to add albums that have broken cover art to the -Torrents with broken cover art links- collage
def post_to_collage(torrent_id, cover_url, collage_type):
    global collage_ajax_page
    global headers
    global collage_message
    global collage_error

    # assign collage ID, name and URL
    if collage_type == "broken_missing_covers_collage":
        collage_id = "31445"
        collage_name = "'Torrents with broken cover art links'"
        collage_url = f"https://redacted.ch/collages.php?id={collage_id}"
    elif collage_type == "bad_covers_collage":
        collage_id = "31735"
        collage_name = "'Torrents with poor quality cover art images'"
        collage_url = f"https://redacted.ch/collages.php?id={collage_id}"

    # create the ajax page and data
    ajax_page = f"{collage_ajax_page}{collage_id}"
    data = {"groupids": torrent_id}
    # post to collage
    r = requests.post(ajax_page, data=data, headers=headers)
    # report status
    status = r.json()
    if status["response"]["groupsadded"]:
        print(f"--Adding release to the {collage_name} collage was a success.")
        print(f"--Logged cover being added to {collage_name}.")
        log_name = "collage_added"
        log_message = f"had bad or missing art and was added to the {collage_name} collage. \nCollage Location: {collage_url}\nTorrent info below"
        log_outcomes(torrent_id, cover_url, log_name, log_message)
        collage_message += 1  # variable will increment every loop iteration
    elif status["response"]["groupsduplicated"]:
        print(f"--Error: Adding release to {collage_name} collage was a failure, the album was already in the collage.")
        print(f"--Logged cover failing to be added to {collage_name} due to it already being in the collage.")
        log_name = "collage_fail"
        log_message = f"had bad or missing art and failed to be added to the {collage_name} due to it already being in the collage. \nCollage Location: {collage_url}\nTorrent info below"
        log_outcomes(torrent_id, cover_url, log_name, log_message)
        collage_error += 1  # variable will increment every loop iteration
    else:
        print(f"--Error: Adding release to {collage_name} collage was a failure.")
        print(f"--Logged cover failing to be added to {collage_name}.")
        log_name = "collage_fail"
        log_message = f"had bad or missing art and failed to be added to the {collage_name}. \nCollage Location: {collage_url}\nTorrent info below"
        log_outcomes(torrent_id, cover_url, log_name, log_message)
        collage_error += 1  # variable will increment every loop iteration


# A function that replaces the existing cover art on RED with the newly hosted one
def post_to_RED(torrent_id, new_cover_url, original_cover_url):
    global count
    global headers
    global site_ajax_page
    global RED_api_error
    global RED_replace_error
    cover_url = original_cover_url

    # create the ajax page and data
    ajax_page = f"{site_ajax_page}{torrent_id}"
    edit_message = "Automatically rehosted cover to PTPimg"
    data = {"summary": edit_message, "image": new_cover_url}

    # replace the cover art link on RED and leave edit summary
    try:
        r = requests.post(ajax_page, data=data, headers=headers)
        status = r.json()
        if status["status"] == "success":
            print(f"--Success: Replacing the cover on RED was a {status['status']}")
            count += 1  # variable will increment every loop iteration
        elif status["error"] == "No changes detected.":
            print(f"--Failure: Replacing the cover on RED was a {status['status']}")
            print("--This album has already had it's cover replaced on RED.")
            print("--Logged cover being skipped due to already having been replaced.")
            log_name = "RED_api_error"
            log_message = "has already had it's cover replaced on RED."
            log_outcomes(torrent_id, cover_url, log_name, log_message)
            RED_replace_error += 1  # variable will increment every loop iteration
        else:
            print(f"--Failure: Replacing the cover on RED was a {status['status']}")
            print(
                "--There was an issue connecting to or interacting with the RED API. If it is unstable, please try again later."
            )
            print("--Logged cover skipped due failed upload to RED.")
            log_name = "RED_api_error"
            log_message = (
                "There may have been an issue connecting to the RED API. If it is unstable, please try again later"
            )
            log_outcomes(torrent_id, cover_url, log_name, log_message)
            # if it is a missing image, post it to the missing covers collage
            collage_type = "broken_missing_covers_collage"
            post_to_collage(torrent_id, cover_url, collage_type)
            RED_replace_error += 1  # variable will increment every loop iteration
    except:
        print("--Failure: There was an issue connecting to or interacting with the RED API. Please try again later.")
        print("--Logged cover skipped due to an issue connecting to the RED API.")
        log_name = "RED_api_error"
        log_message = (
            "There may have been an issue connecting to the RED API. If it is unstable, please try again later"
        )
        log_outcomes(torrent_id, cover_url, log_name, log_message)
        # if it is a missing image, post it to the missing covers collage
        collage_type = "broken_missing_covers_collage"
        post_to_collage(torrent_id, cover_url, collage_type)
        RED_api_error += 1  # variable will increment every loop iteration
        return


# A function that rehosts the cover to ptpimg
def rehost_cover(torrent_id, cover_url):
    global p_api_key
    global ptpimg_api_error

    # TODO: Do this once globally
    # Instantiate an uploader
    ptpimg = ptpimg_uploader.PtpimgUploader(api_key=p_api_key, timeout=10)

    try:
        # Upload URL
        new_cover_url = ptpimg.upload_url(cover_url)

        if new_cover_url:
            new_cover_url = new_cover_url[0].strip()
            print(f"--The cover has been rehosted at {new_cover_url}")
            return new_cover_url

        else:
            print(
                "--Failure: The cover was missing from the internet. Please replace the image manually. If the image is there, then the site resisted being scraped or there was an issue connecting to or interacting with PTPimg."
            )
            print(
                "--Logged cover skipped due to it being no longer on the internet or there being an issue connecting to the ptpimg API."
            )
            log_name = "cover_missing"
            log_message = "albums cover is missing from the internet or the site is blocking scraping images. Please replace the image manually. If the image is there, it is possible that it was skipped due to an issue connecting to the ptpimg API. Please try again later"
            log_outcomes(torrent_id, cover_url, log_name, log_message)
            ptpimg_api_error += 1  # variable will increment every loop iteration

            # TODO: This collage logic feels like it belongs elsewhere
            # if it is a missing image, post it to the missing covers collage
            collage_type = "broken_missing_covers_collage"
            post_to_collage(torrent_id, cover_url, collage_type)

    except:  # TODO: Improve exception handler
        print("--Failure: There was an issue rehosting the cover art to ptpimg. Please try again later.")
        print("--Logged cover skipped due to an issue connecting to the ptpimg API.")
        log_name = "ptpimg-api-error"
        log_message = "was skipped due to an issue connecting to the ptpimg API. Please try again later"
        log_outcomes(torrent_id, cover_url, log_name, log_message)
        ptpimg_api_error += 1  # variable will increment every loop iteration

    return


# A function to introduce a random delay into the loop to reduce the chance of being blocked for web scraping.
def loop_delay():
    global count
    if count >= 1:
        delay = randint(1, 3)  # Generate a random number of seconds within this range
        print(f"The script is pausing for {delay} seconds.")
        sleep(delay)  # Delay the script randomly to reduce anti-web scraping blocks


# A function to check a series of conditions on the cover url before it is attempted to be rehosted.
def url_condition_check(torrent_id, cover_url):
    global cover_missing_error

    # First check if we should even bother

    host = str(urlparse(cover_url).hostname)

    # Is the host going to give us a crappy image?

    if host in LOW_QUALITY_HOSTS:
        print("--Failure: Cover skipped due to it being on a site that has watermarked or tiny images.")
        print("--Logged cover as missing cover, image is watermarked or tiny.")
        log_name = "cover_missing"
        log_message = "cover was skipped due to it being hosted on a site that has watermarked or tiny images"
        log_outcomes(torrent_id, cover_url, log_name, log_message)
        cover_missing_error += 1  # variable will increment every loop iteration
        # if it is a bad cove host, post it to the bad covers collage
        collage_type = "bad_covers_collage"
        post_to_collage(torrent_id, cover_url, collage_type)
        return False

    # Is the host known to be dead?
    if host in BAD_HOSTS:
        print("--Failure: Cover is no longer on the internet. The site that hosted it is gone.")
        print("--Logged missing cover, site no longer exists.")
        log_name = "cover_missing"
        log_message = "cover is no longer on the internet. The site that hosted it is gone"
        log_outcomes(torrent_id, cover_url, log_name, log_message)
        cover_missing_error += 1  # variable will increment every loop iteration
        # if it is a missing image, post it to the missing covers collage
        collage_type = "broken_missing_covers_collage"
        post_to_collage(torrent_id, cover_url, collage_type)
        return False

    # We've passed basic checks, try to load the image

    try:
        r = requests.get(cover_url)  # Here is where im getting the error
        r.raise_for_status()
    except requests.exceptions.HTTPError:
        print("--Failure: Cover is no longer on the internet. The site that hosted it is gone.")
        print("--Logged missing cover, site no longer exists.")
        log_name = "cover_missing"
        log_message = "cover is no longer on the internet. The site that hosted it is gone"
        log_outcomes(torrent_id, cover_url, log_name, log_message)
        cover_missing_error += 1  # variable will increment every loop iteration
        # if it is a missing image, post it to the missing covers collage
        collage_type = "broken_missing_covers_collage"
        post_to_collage(torrent_id, cover_url, collage_type)
        return False

    # did we get redirected?
    if r.history:
        final_url = r.url
        print(f"--The url was forwarded to {final_url}")

        # Is the host returning a bogus image instead of a 404?
        if TRICKY_HOSTS.get(host) == final_url:
            print("--Failure: Cover is no longer on the internet. It was replaced with a 404 image.")
            print("--Logged album skipped due to bad host.")
            log_name = "cover_missing"
            log_message = "cover is no longer on the internet. It was replaced with a 404 image"
            log_outcomes(torrent_id, cover_url, log_name, log_message)
            cover_missing_error += 1  # variable will increment every loop iteration
            # if it is a 404 image, post it to the missing covers collage
            collage_type = "broken_missing_covers_collage"
            post_to_collage(torrent_id, cover_url, collage_type)
            return False

    return True


# A function that check if text file exists, loads it, loops through the lines, get id and url
def loop_rehost():
    global list_error
    global list_directory
    global total_count

    # assemble list path
    list_path = os.path.join(list_directory, "list.txt")

    # load the list of torrent ids and cover urls and cycle through them
    # check to see if there is an text file
    if os.path.exists(list_path):
        # open the txt file and get the torrent group ID and cover url
        try:
            with open(list_path, encoding="utf-8") as f:
                reader = DictReader(f, dialect="unix")
                for line in reader:

                    torrent_id: int = int(line["ID"])
                    cover_url: str = line["WikiImage"].strip()
                    print("")
                    print("Rehosting:")
                    total_count += 1  # variable will increment every loop iteration
                    print(f"--The group url is https://redacted.ch/torrents.php?id={torrent_id}")
                    print(f"--The url for the cover art is {cover_url}")

                    # TODO: This issues a GET, and then the ptpimg_uploader does another one inside of rehost_image -- find a way to avoid doubling.
                    # check to see if the site is there and whether the image is a 404 image
                    site_condition = url_condition_check(torrent_id, cover_url)
                    if site_condition:
                        # run the rehost cover function passing it the torrent_id and cover_url
                        new_cover_url = rehost_cover(torrent_id, cover_url)
                        # trigger function to post cover to RED
                        if new_cover_url:
                            post_to_RED(torrent_id, new_cover_url, cover_url)

                    # introduce a delay after the first cover is rehosted
                    loop_delay()

        except FileNotFoundError:
            print(
                "--Error: The list.txt file is missing or named something else and the cover could not be rehosted. Please check it."
            )
            list_error += 1  # variable will increment every loop iteration
            return
        except IndexError:
            print(
                "--Error: There was an issue parsing the list.txt file and the cover could not be rehosted. It was likely due to a blank line existing either before or after the list of links. Please check it."
            )
            list_error += 1  # variable will increment every loop iteration
            return
    else:
        print("--The list of ids and album covers is missing.")
        list_error += 1  # variable will increment every loop iteration


# The main function that controls the flow of the script
def main():
    try:
        # intro text
        print("")
        print("You spin me right 'round, baby, right 'round...")

        # Run the function to loop through the list.txt file and rehost the cover art
        loop_rehost()

    finally:
        # Summary text
        print("")
        print("Like a record, baby, right 'round, 'round, 'round...")
        # run summary text function to provide error messages
        summary_text()
        print("")


if __name__ == "__main__":
    main()
