#!/bin/sh
###########################################
####  v2v project install shell file    ###
####  2016/1/14                         ###
###########################################

#v2v gateway service IP
GATEWAYI_SERVICE_IP=0.0.0.0
GATEWAYI_SERVICE_PORT=9998


#v2v gateway service name
GATEWAY_SERVICE_NAME=conveyoragent
ROOTWRAP_SERVICE_NAME=conveyor-rootwrap
#v2v gateway service user name
GATEWAYI_REGISTER_USER_NAME=conveyor
#v2v gateway service register user password
GATEWAY_REGISTER_USER_PASSWD=Huawei123
#v2v gateway role name
GATEWAY_REGISTER_ROLE_NAME=admin
#v2v gateway register relation tenant name
GATEWAY_REGISTER_TENANT_NAME=service
#v2v gateway service register name
GATEWAY_REGISTER_SERVICE_NAME=v2vGateWay
#v2v api service register service type
GATEWAY_REGISTER_SERVICE_TYPE=v2vGateWay

#source code file directory
CODE_DIR=/usr/lib/python2.6/site-packages
CONFIG_DIR=/etc/conveyoragent
BIN_DIR=/usr/local/bin
GATEWAY_CONFIG_FILE=hybrid-v2v.conf

#CONSISTENT VARIABLE VALUE
LOG_DIR=/var/log/conveyoragent
LOG_FILE=${LOG_DIR}/install.log
TIME_CMD=`date '+%Y-%m-%d %H:%M:%S'`
BOOL_TRUE_INT=0
BOOL_FALSE_INT=1
ERROR_INT=2

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

#####################################################################
# Function: system_check
# Description: v2v service relies openstack(keystone), so system must
#               install openstack first.
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
system_check()
{
   keystoneservice=${keystone service-list | awk '/ keystone / {print $2}'}
   if [ $? -ng 0 ]; then
      #log error
      return 1
   fi
   
   return 0
}


#####################################################################
# Function: check_gateway_register_user_exist
# Description: check gateway user info is registered or not
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
check_gateway_register_user_exist()
{
    user=$(keystone user-list | awk '/ '${GATEWAYI_REGISTER_USER_NAME}' / {print $2}')
	
	if [ $? -ne 0 ]; then
	   echo ${TIME_CMD} "check v2v api register user error" >> "${LOG_FILE}"
	   keystone user-list | awk '/ '${GATEWAYI_REGISTER_USER_NAME}' / {print $2}'  >> "${LOG_FILE}" 2>&1
	   return ${ERROR_INT}
	fi
	
	#check is null
	if [ -z $user ]; then
	    #is null
		echo ${TIME_CMD} "check v2v api register user is null" >> "${LOG_FILE}"
	    return ${BOOL_TRUE_INT}
	else
	    #other
		echo ${TIME_CMD} "check v2v api register user is " "${user}" >> "${LOG_FILE}"
	    return ${BOOL_FALSE_INT}
	fi
}

#####################################################################
# Function: copy_files_to_dir
# Description: copy v2v project files to install directory
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
copy_files_to_dir()
{
    #make code directory
    if [ ! -d ${CODE_DIR} ]; then
       mkdir -p ${CODE_DIR}
    fi
    
    
    #copy  running file to /usr/local/bin
    for f in ${ROOTWRAP_SERVICE_NAME} ${GATEWAY_SERVICE_NAME}; do
	
	    if [ -f ${BIN_DIR}/$f ]; then
		    rm -f ${BIN_DIR}/$f
		fi
		
        cp $f ${BIN_DIR}
		
		if [ ! -x ${BIN_DIR}/$f ]; then
		  chmod +x ${BIN_DIR}/$f
		fi
		 
    done 

    #copy source code to /usr/local/lib/python2.7/dist-packages
	if [ -d ${CODE_DIR}/conveyoragent ]; then
	   rm -rf ${CODE_DIR}/conveyoragent
	fi
    cp -r ../conveyoragent ${CODE_DIR}
    
    #copy dependence file to excute directory
    cp -r ../bin/depend/*  ${CODE_DIR}
   
    #make config file directory
	if [ -d ${CONFIG_DIR} ]; then
	   rm -rf ${CONFIG_DIR}
	fi
	
    mkdir ${CONFIG_DIR}

    #copy config file to /etc/v2v
    cp -r ../etc/conveyoragent/* ${CONFIG_DIR}
}


#####################################################################
# Function: register_gateway_services
# Description: register gateway services info to keystone
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
register_gateway_services()
{
    #check user is register or not
    check_gateway_register_user_exist
	
	if [ $? -eq ${ERROR_INT} ]; then
	   echo  ${TIME_CMD} "error: v2v gateway register user error, check user failed" >> "${LOG_FILE}"
	   return ${ERROR_INT}	   
	fi
	if [ $? -eq ${BOOL_TRUE_INT} ]; then
        #register the user of v2v service 
        keystone user-create --name=${GATEWAYI_REGISTER_USER_NAME} --pass=${GATEWAY_REGISTER_USER_PASSWD} --email=admin@example.com

        #register v2v user and tenant relation (eg: service Tenant / admin Role)
        keystone user-role-add --user=${GATEWAYI_REGISTER_USER_NAME} --tenant=${GATEWAY_REGISTER_TENANT_NAME} \
		--role=${GATEWAY_REGISTER_ROLE_NAME} >> "${LOG_FILE}" 2>&1
	else
	   echo  ${TIME_CMD} "warning: v2v gateway register user exist. there not register. user name: " \
  	   "${GATEWAYI_REGISTER_USER_NAME}" >> "${LOG_FILE}"
	fi  	   	
    #register v2v service 
    keystone service-create --name=${GATEWAY_REGISTER_SERVICE_NAME} --type=${GATEWAY_REGISTER_SERVICE_TYPE} --description="v2v gateway service"

    #register v2v endpoint
	serviceId=$(keystone service-list | awk '/ '${GATEWAY_REGISTER_SERVICE_NAME}' / {print $2}')
    keystone endpoint-create --region=RegionOne --service-id=${serviceId} \
	--publicurl=http://${GATEWAYI_SERVICE_IP}:${GATEWAYI_SERVICE_PORT}/v1/$\(tenant_id\)s \
	--adminurl=http://${GATEWAYI_SERVICE_IP}:${GATEWAYI_SERVICE_PORT}/v1/$\(tenant_id\)s  \
	--internalurl=http://${GATEWAYI_SERVICE_IP}:${GATEWAYI_SERVICE_PORT}/v1/$\(tenant_id\)s >> "${LOG_FILE}" 2>&1
	
	if [ $? -ne 0 ]; then
	   echo "create endpoint failed" >> "${LOG_FILE}"
	   return ${ERROR_INT}
	fi
}


#####################################################################
# Function: start_gateway_service
# Description: start gateway service
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
start_gateway_service()
{
    ${BIN_DIR}/${GATEWAY_SERVICE_NAME} --config-file ${CONFIG_DIR}/${GATEWAY_CONFIG_FILE} &
    
    if [ $? -ne 0 ]; then
       echo  ${TIME_CMD} "start gateway service error." >> "${LOG_FILE}"
	   ${BIN_DIR}/${GATEWAY_SERVICE_NAME} --config-file ${CONFIG_DIR}/${GATEWAY_CONFIG_FILE} & >> "${LOG_FILE}" 2>&1
    fi	
}


#####################################################################
# Function: reset_gateway_config_file
# Description: reset gateway service starting config file
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
reset_gateway_config_file()
{
	#reset v2v gateway config info
	sed -i "s:#GATEWAY_V2V_LISTEN_IP#:${GATEWAYI_SERVICE_IP}:g" ${CONFIG_DIR}/${GATEWAY_CONFIG_FILE}
	sed -i "s:#GATEWAY_V2V_LISTEN_PORT#:${GATEWAYI_SERVICE_PORT}:g" ${CONFIG_DIR}/${GATEWAY_CONFIG_FILE}
	#reset keystone config info
	sed -i "s:#AUTH_URL_IP#:${AUTH_URL_IP}:g" ${CONFIG_DIR}/${GATEWAY_CONFIG_FILE}
	sed -i "s:#AUTH_URL_PORT#:${AUTH_URL_PORT}:g" ${CONFIG_DIR}/${GATEWAY_CONFIG_FILE}
    sed -i "s:#AUTH_USER_NAME#:${AUTH_ADMIN_USER}:g" ${CONFIG_DIR}/${GATEWAY_CONFIG_FILE}
	sed -i "s:#AUTH_USER_PASSWD#:${AUTH_ADMIN_PASSWD}:g" ${CONFIG_DIR}/${GATEWAY_CONFIG_FILE}
}

#####################################################################
# Function: main
# Description: main func
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
main()
{
    #check system
	#system_check
	
	generate_log_file
	copy_files_to_dir

	reset_gateway_config_file
	   
	start_gateway_service
}

main $@




