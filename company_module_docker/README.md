# Project: smashHit

Solving Consumer Consent & Data Security for Connected Car and Smart City

## Data Traceability Module (current repository/folder)

Traceability module of the data traceability project made exclusively for use by any company participating in smashHit. This folder/repository is the part of the smashHit platform which enables the tracking of data packages within the smashHit system.

## Contributors

Developed By: University of Bonn(UBO) and Leibniz Universität Hannover (LUH) <br> Other Project Partners: Institute for Applied Systems Technology Bremen (ATB), Leopold-Franzens-Universität Innsbruck (UIBK), Atos Information Technology GmbH (ATOS), InfoTripla

## Business Organizations

Volkswagen, LexisNexis

## Getting started with the repository

1. The data traceability project has two major components, Traceability Manager and Traceability Module. This repository contains only the Traceability Module. The Traceability Manager is deployed on the server - http://smashhit.l3s.uni-hannover.de/swagger-ui/
2. This Traceability Module communicates with manager to handle the user requests using the above deployed manager and reference of this url can be found in util.py of this repository set as value to variable 'url_to_manager' in line number 10.
3. To get started, clone this repository or extract files from the zip.
4. Install all the libraries as provided in the requirements.txt and then main.py can be straight away run and then by opening http://localhost:5001/swagger-ui/ on browser, all APIs facilitated by this company module will become accessible, all communicating with the deployed manager. By default, as set in the main.py, the module runs with a default smashhit_name of 'UBO_sender'. Only when you intend to confirm the receipt of data as a receiver company, a suitable name like 'UBO_receiver' can be set in this smashhit_name field of main.py and then main.py should be re-run and then confirm data transfer API as listed on the UI can be used. In real world scenario, during on-boarding of a company on smashhit platform, smashhit names for each company module should be set e.g. ATOS instead of UBO_sender and fixed permanently for use in future. Give and take of public and private keys will happen during 1st time use of the module by the company with given specific smashhit_name.
5. Steps in point 4 above, can be skipped if you wish to use docker. If you wish to use docker for this module and not as standalone component mentioned in step 4, only then, build the docker image by running the following command in terminal once the control is inside the company_module/src folder: <b>docker build -t data_use_traceabilty . </b> . The smashhit name(or unique identity) of the company needs to be set inside the CMD command of the Dockerfile, which for now is set as 'sender' as default. After ensuring no other service is running on port 5001 of the localPC/server, run the docker container using the following command: <br/> <b>docker run -p 5001:5001 -it data_use_traceabilty </b> <br/>

So, for now for testing purposes, this command runs the module as data sender as it is set in the Dockerfile. For testing purposes, 2 separate modules can be set up by running docker at separate ports with one being the data sender and other being the data receiver(thereby setting CMD of Dockerfile accordingly). <br/>

Else, with just 1 instance of the module run, we can do this in by overriding teh default value of smashhit_name. For this, while running module as data raceiver, for purpose of confirming the receipt of data, then during the run of Docker, following can be passed as argument to override the defaut sender argument inside Dockerfile. <br/> <b>docker run -p 5001:5001 -it data_use_traceabilty --smashhit_name='receiver' </b> <br/>

By default the url to manager is set as the manager's deployment at Hannover University's server i.e. 'http://smashhit.l3s.uni-hannover.de' If that needs to be changed and maybe connection needs to be made to a server running on for example localhost:5000, then following command needs to be made.

<b>docker run -p 5001:5001 -it data_use_traceabilty --smashhit_name='receiver' --url_to_manager='http://localhost:5000' </b> <br/>

Both arguments passed during docker runtime are optional, in absence of which default values are used by the program.

P.S. The default port of 5001 used here can be changed to any available port but for that, inside api.py, we need to change the port accordingly.

6. While confirming the data transfer by the receiving company, signature_of_sender from the UI should be set as what was received in response at UI during notify_data_transfer functionality.
7. On browser, use - http://localhost:5001/swagger-ui/ or the ip address provided in the terminal where docker run command was fired. For ease of use, swagger-ui is used here to provide inputs. The user can also have his own UI and just call the API's for functionalities of register,
8. init_transfer, confirm_transfer, consent_trace and contract_trace
9. To learn about the manager and module contents more in details, please refer to the readme of the main git repository with following link https://git.l3s.uni-hannover.de/smashhit/data_use_traceability , or readme in that provided zipped folder.