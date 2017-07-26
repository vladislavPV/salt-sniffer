# salt-sniffer.
### Listens on salt event bus and post events to slack

`salt-sniffer` is a small Python application which runs on the same instance with salt-master and listens events on salt event bus
after intercepting event it will send it to the slack channel
You can find more info about salt event bus on
https://docs.saltstack.com/en/2015.8/topics/event/index.html

### Install
install slacker
   pip install slacker

Download salt-sniffer.py
You can instantiate it by using supervisord, systemd, upstart or any other init system

### Config
Configuration is done using environment variables
Before running app you have to add:
Mandatory:
	export SLACK_TOKEN='xoxb-5654646464646-kjdshfksjbfksjbfkerere'
Other:
	export EXCLUDE_FUNS=saltutil.find_job,test.ping #you can filter functions
	export EXCLUDE_USERS="testuser" #you can filter users
	export EXCLUDE_ARGS=/etc/portage/make.conf #you can filter arguments
	export SLACK_MSG_LIMIT=4 #number of slack messages per salt batch
	export SLACK_CHANNEL=#general
	export MASTER_CONF=/etc/salt/master

### Run
```
$ sudo python salt-sniffer.py
```

### Test
create file local_env with env vars

export SLACK_TOKEN='xoxb-234234234-sfgsfgsfgsfgsfgsfgsfg'
export SLACK_CHANNEL=#general

build/run docker container:
  ./bin/run-docker

run app:
  python salt-sniffer.py


connect to container:
  docker exec ${container-name} bash

run salt command
  salt'*' test.ping