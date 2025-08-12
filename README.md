This repository contains two, currently unmerged, repositories: **Announcements** and **Service**. The deprecated folder conatins files that may have some use as reference material, but are currently not part of any pipeline. Connecting to Planning Center requires API keys that are not included in this repository.

# Announcements
Running `main.py` in this repository creates the announcement .pptx file and the .jpg files of each slide in the .pptx file. Running `main.py` will ask for authorization to a Google account. The announcements are created by reading the weekly E-vents email that goes out and parsing the content in to slides. The information in the email is summarized by a text-bison LLM model if the title or body text is too long to fit in the PowerPoint slide. This process requires authenitcation with Google's Vertext AI platform. Additional users likely need to be configured for anyone other than Kory to run this at present.

The slides are uploaded to each Planning Center service for the upcoming week and saved locally.

# Service
Running `make_pro.py` connects to Planning Center Online to access all of the items for each service for the next Sunday. Text in each item is parsed and broken into text chunks that are an appropriate length for each ProPresenter slide. Each item that needs a ProPresenter presentaiton (e.g. Centering Words, Opening Prayer) gets a presentation made from it's text by pulling the appropriate ProPresenter template (white, yellow, blank) and replacing the text. The .pro files get uploaded to their corresponding Planning Center item. 

.pro files are Google Protocol Buffer files. You can learn more about what these files are, how ProPresenter uses them, and how to use them in different programming languages in `/service/ProPresenter7_Proto` which is a fork of greyshirtguy's repository who did much of the legwork on decoding these undocumented files. That repository contains its own README.
