#!/home/stellarmate/anaconda3/bin/python3
import diy21cm as d21

# here is another change
   
# Turn on bias T to power LNA
d21.biasTOn()


# keep track of start date,
# in case the observing session runs past midnight
# into the following day
paramStart = d21.getDefaultParams()
d21.setDate(paramStart)


# Take repeated exposures
while(True):

   try:
      # For each exposure
      param = d21.getDefaultParams()

      # Change exposure time if desired
      param['integrationTime'] = 5*60  # [sec]

      d21.setExpType(param, 'on')
      #V}d21.setExpType(param, 'foff')
      #d21.setExpType(param, 'fswitch')
      #d21.setExpType(param, 'cold')
      #d21.setExpType(param, 'hot')


      # set the same date as the start ofthe observing session,
      # and add 24 to the hours for each day elapsed
      # this way all output files are in the same folder,
      # even if we cross midnight
      d21.setTimeSameDate(param, paramStart)

      d21.setMountInfo(param)

      d21.setOutputFigDir(param)
      d21.setFileName(param)

      d21.takeExposure(param)
      d21.attemptCalibration(param)

      d21.saveJson(param)
      d21.savePlot(param)

      # take a screenshot for the timelapse
      # after some time, so the open figures
      # have time to update
      d21.time.sleep(5) # delay in [sec]
      d21.saveScreenshot(param)

   except:
      print("Something went wrong with this exposure. Trying again...")

# Turn off bias T to power off LNA
#d21.biasTOff()
