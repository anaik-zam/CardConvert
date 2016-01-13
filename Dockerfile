FROM ubuntu:14.04
MAINTAINER Aditya Naik <anaik@zam.com>

RUN apt-get update

# to install  add-apt-repository which will be used to install ffmpeg
RUN apt-get --assume-yes install software-properties-common

# install python and pyyaml
RUN apt-get --assume-yes install python2.7 python-yaml

# install png utilities apngasm & apng2gif
RUN apt-get --assume-yes install apngasm apng2gif

## ffmpeg
RUN  add-apt-repository -y ppa:mc3man/trusty-media
RUN apt-get update
#RUN apt-get dist-upgrade
RUN apt-get --assume-yes install ffmpeg

## imagemagick
RUN apt-get --assume-yes install imagemagick

# copy the CardConvert project
Add . /CardConvert

## set the env vars
ENV PATH /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/CardConvert/bin
ENV PYTHONPATH /CardConvert/python
ENV CARDCONVERT_CONFIG /CardConvert/config/CardConvert.yaml
ENV BACKGROUNDS_FOLDER /CardConvert/backgrounds


## make the log folder
#RUN mkdir /var/log/CardConvert

## execute the card convert script
CMD ["pycc", "/input", "/output"]

#docker build --no-cache -t anaik/cc:latest .
#docker run -v /home/anaik/input:/input -v /home/anaik/foo:/output -v /var/log/CardConvert:/var/log/CardConvert -t -i anaik/cc /bin/bash
