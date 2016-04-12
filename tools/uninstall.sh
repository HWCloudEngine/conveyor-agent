#!/bin/sh
###########################################
####  v2v project uninstall shell file  ###
####  2016/1/14                         ###
###########################################


#v2v gateway service name
GATEWAY_SERVICE_NAME=conveyoragent
#v2v gateway service user name
GATEWAYI_REGISTER_USER_NAME=v2v
#v2v gateway role name
GATEWAY_REGISTER_ROLE_NAME=admin
#v2v gateway service register name
GATEWAY_REGISTER_SERVICE_NAME=v2vGateWay
#v2v gateway register relation tenant name
GATEWAY_REGISTER_TENANT_NAME=service

#source code file directory
V2V_CODE_DIR=/usr/lib/python2.6/site-packages/conveyoragent
OSLO_CODE_DIR=/usr/lib/python2.6/site-packages/birdiegateway
CONFIG_DIR=/etc/conveyoragent
BIN_DIR=/usr/local/bin
LOG_DIR=/var/log/conveyoragent
LOG_FILE=${LOG_DIR}/v2v_uninstall.log
TIME_CMD=`date '+%Y-%m-%d %H:%M:%S'`

#####################################################################
# Function: generate_log_file
# Description: generate log file
# Parameter:
# input:
# $1 -- NA 
# $2 -- NA
# output: NA
# Return:
# RET_OK
# Since: 
#
# Others:NA
#######################################################################
generate_log_file()
{ 
    if [ ! -d ${LOG_DIR} ]; then
	   mkdir -p ${LOG_DIR}
	fi
	
	if [ ! -f ${LOG_FILE} ]; then
	   touch ${LOG_FILE}
	fi
}



####################################################################
# Function: stop_gateway_service
# Description: stop v2v gateway service (kill this service process).
# Parameter:
# input:
# $1 -- NA 
# $2 -- NA
# output: NA
# Return:
# RET_OK
# Since: 
#
# Others:NA
#####################################################################
stop_gateway_service()
{
    ps aux|grep ${GATEWAY_SERVICE_NAME}|awk '{print $2}'|xargs kill -9
	
	if [ $? -eq 0 ]; then
	    echo  ${TIME_CMD} "stop gateway service success" >> "${LOG_FILE}"
	else
	  #log error
	   echo  ${TIME_CMD} "stop gateway service error" >> "${LOG_FILE}"
	fi
}

####################################################################
# Function: clear_files
# Description: clear v2v project files.
# Parameter:
# input:
# $1 -- NA 
# $2 -- NA
# output: NA
# Return:
# RET_OK
# Since: 
#
# Others:NA
#####################################################################
clear_files()
{
    #remove bin file 
    rm -f ${BIN_DIR}/${GATEWAY_SERVICE_NAME}
	
	#remove source code files
	rm -rf ${V2V_CODE_DIR}
	#rm -rf ${OSLO_CODE_DIR}
	
	#remove config files
	rm -rf ${CONFIG_DIR}
}


####################################################################
# Function: main
# Description: main func.
# Parameter:
# input:
# $1 -- NA 
# $2 -- NA
# output: NA
# Return:
# RET_OK
# Since: 
#
# Others:NA
#####################################################################
main()
{
   generate_log_file
   #stop service 
   stop_gateway_service
   
   #clear all files
   clear_files
}

main $@


