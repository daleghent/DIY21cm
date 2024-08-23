#!/home/stellarmate/anaconda3/bin/python3
import diy21cm as d21
   
# Turn on bias T to power LNA
d21.biasTOn()

# For each exposure
param = d21.getDefaultParams()

# Change exposure time if desired
param['integrationTime'] = 5 #5*60  # [sec]

d21.setExpType(param, 'on')
#d21.setExpType(param, 'foff')
#d21.setExpType(param, 'fswitch')
#d21.setExpType(param, 'cold')
#d21.setExpType(param, 'hot')

d21.setDate(param)
d21.setTime(param)
d21.setMountInfo(param)

d21.setOutputFigDir(param)
d21.setFileName(param)

d21.takeExposure(param)
d21.attemptCalibration(param)

d21.saveJson(param)
d21.savePlot(param)

# Turn off bias T to power off LNA
#d21.biasTOff()
