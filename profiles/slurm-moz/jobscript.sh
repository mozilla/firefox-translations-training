#!/bin/bash
# properties = {properties}
export http_proxy="http://192.168.1.1:3128/"
export https_proxy="http://192.168.1.1:3128/"
export ftp_proxy="http://192.168.1.1:3128/"
export no_proxy="localhost,127.0.0.1,::1,.mlc,192.168.1.1,10.2.224.243"

export HTTP_PROXY="http://192.168.1.1:3128/"
export HTTPS_PROXY="http://192.168.1.1:3128/"
export FTP_PROXY="http://192.168.1.1:3128/"
export NO_PROXY="localhost,127.0.0.1,::1,.mlc,192.168.1.1,10.2.224.243"

export SINGULARITYENV_CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES

{exec_job}