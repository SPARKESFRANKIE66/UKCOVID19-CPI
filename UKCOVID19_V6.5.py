from datetime import date, datetime, timedelta
from gpiozero import LED
from iso3166 import countries
from json import dumps, loads
from uk_covid19 import Cov19API
import asyncio, discord, flag, lcddriver, os, requests, time, traceback

# Global Constants
VersionNum = "6.5.1b"
BeginTime = "1540"
DelayTime = 15
DataAggregationTemplate = {
  "Date": None,
  "Day": None,
  "Cases": {
    "New": None,
    "Change": None,
    "RollingAverages": {
      "Three": {
        "Average": None,
        "Change": None,
      },
      "Seven": {
        "Average": None,
        "Change": None
      }
    },
    "Corrections": None,
    "Total": None
  },
  "Deaths": {
    "New": None,
    "Change": None,
    "RollingAverages": {
      "Three": {
        "Average": None,
        "Change": None,
      },
      "Seven": {
        "Average": None,
        "Change": None
      }
    },
    "Corrections": None,
    "Total": None
  },
  "CaseFatality": {
    "Rate": None,
    "Change": None
  }
}
TimeoutCondition = "1500"

# COVID API Constants
Filters = [
  "areaType=Overview",
  "areaName=United Kingdom"
]
PrimaryStructure = {
  "Date": "date",
  "CasesNew": "newCasesByPublishDate",
  "DeathsNew": "newDeaths28DaysByPublishDate",
  "CasesTotal": "cumCasesByPublishDate",
  "DeathsTotal": "cumDeaths28DaysByPublishDate"
}
PrimaryLatestBy = "newCasesByPublishDate"
SecondaryStructure = {
  "Date": "date",
  "VaccinationsFirstDoseNew": "newPeopleVaccinatedFirstDoseByPublishDate",
  "VaccinationsFirstDoseTotal": "cumPeopleVaccinatedFirstDoseByPublishDate",
  "VaccinationsSecondDoseNew": "newPeopleVaccinatedSecondDoseByPublishDate",
  "VaccinationsSecondDoseTotal": "cumPeopleVaccinatedSecondDoseByPublishDate",
  "VaccinationsAdditionalDoseNew": "newPeopleVaccinatedThirdInjectionByPublishDate",
  "VaccinationsAdditionalDoseTotal": "cumPeopleVaccinatedThirdInjectionByPublishDate"
}
SecondaryLatestBy = "newPeopleVaccinatedFirstDoseByPublishDate"

# COVID API Instantiations
PrimaryAPI = Cov19API(Filters, PrimaryStructure, PrimaryLatestBy)
SecondaryAPI = Cov19API(Filters, SecondaryStructure, SecondaryLatestBy)

# COVID Pi GPIO Constants
Display = lcddriver.lcd()
ErrorLED = LED(14)
OldLED = LED(15)
NewLED = LED(18)

# Discord Constants
DiscordClient = discord.Client()
BotToken = ""
ChannelID = 0

# Directories
RootFolder = "/home/pi/Documents/UKCOVID19/"
ErrorLogsRootFolder = RootFolder + "Logs/ErrorLogs/"
RuntimeLogsRootFolder = RootFolder + "Logs/RuntimeLogs/"
SuppFilesRootFolder = RootFolder + "SuppFiles/"

# Files
AllDataFilename = SuppFilesRootFolder + "AllData.json"
DiscordInfoFilename = SuppFilesRootFolder + "Discord.json"
LogFilename = RuntimeLogsRootFolder + "Log_"
LastOutputFilename = SuppFilesRootFolder + "LastOutput.txt"
RollAvgPeaksFilename = SuppFilesRootFolder + "RAPeaks.json"
VariantsFilename = SuppFilesRootFolder + "Variants.json"

# Status Messages URL and Files
BlueBannersTemplateAddress = "https://coronavirus.data.gov.uk/api/generic/log_banners/"
BlueBannersWebAddresses = [
  BlueBannersTemplateAddress + date.today().isoformat() + "/Cases/overview/United%20Kingdom",
  BlueBannersTemplateAddress + date.today().isoformat() + "/Deaths/overview/United%20Kingdom",
  BlueBannersTemplateAddress + date.today().isoformat() + "/Vaccinations/overview/United%20Kingdom"
]
MessagesFilename = SuppFilesRootFolder + "Messages.json"
YellowBannersWebAddress = "https://coronavirus.data.gov.uk/api/generic/announcements"

# Global Variables
CurrentDisplay = [
  "Cases".center(10) + "|" + "Deaths".center(9),
  "X",
  "X",
  "X"
]
DateOfCurrentData = "1970-01-01"
ErrorMode = False
LatestRecordFormatted = DataAggregationTemplate
PrimaryUpdated = False
SecondaryUpdated = False

# Startup Procedures
def POST():
  Display.lcd_clear()
  Display.lcd_display_string("Welcome to COVID Pi.", 1)
  Display.lcd_display_string("Version " + VersionNum + ".", 2)
  for _ in range(2):
    ErrorLED.on()
    time.sleep(0.5)
    ErrorLED.off()
    OldLED.on()
    time.sleep(0.5)
    OldLED.off()
    NewLED.on()
    time.sleep(0.5)
    NewLED.off()

def WaitForNetwork():
  IPAddresses = [
    "http://192.168.0.1",
    "http://1.1.1.1"
  ]
  ErrorMode = False
  SuccessfulNetworkCheck = False
  OldLED.on()
  Display.lcd_display_string("Waiting for network.", 4)
  WriteToMainLog("Waiting for network connectivity. . .")
  while not SuccessfulNetworkCheck:
    try:
      for i in range(len(IPAddresses)):
        WriteToMainLog("Testing connection to IP address " + IPAddresses[i] + ". . .")
        R = requests.get(IPAddresses[i])
        if R.status_code != 200 and R.status_code != 204:
          raise Exception("Request fail with status code " + str(R.status_code) + " on address " + IPAddresses[i])
        WriteToMainLog("Test completed with status code " + str(R.status_code) + ".")
        if ErrorMode:
          ErrorLED.off()
          OldLED.on()
          ErrorMode = False
        NewLED.on()
        if i == 1:
          OldLED.off()
        time.sleep(2)
      SuccessfulNetworkCheck = True
    except:
      if not ErrorMode:
        OldLED.off()
        ErrorLED.on()
        ErrorMode = True
      PrintError()
      time.sleep(5)
  OldLED.off()
  NewLED.off()

def ReloadLastOutputFromFile():
  global CurrentDisplay, DateOfCurrentData, ErrorMode
  if os.path.isfile(LastOutputFilename):
    if os.path.getsize(LastOutputFilename) > 8:
      with open(LastOutputFilename,'r') as LastOutputFile:
        LastOutput = LastOutputFile.read().split('\n')
      for i in range(len(LastOutput)-1):
        if i == 0:
          Line = LastOutput[i].split(",")
          DateOfCurrentData = Line[0]
          if Line[1] == "True":
            ErrorMode = True
            ErrorLED.on()
        else:
          CurrentDisplay[i-1] = LastOutput[i]
          if CurrentDisplay[i-1] != "X":
            Display.lcd_display_string(CurrentDisplay[i-1],i)
            WriteToMainLog("Written line " + str(i) + " of last output to display.")
      WriteToMainLog("Previous data written to display.")
    else:
      ReloadLastOutputFromReserve()
  else:
    ReloadLastOutputFromReserve()

def ReloadLastOutputFromReserve():
  global CurrentDisplay, DateOfCurrentData, ErrorMode, LatestRecordFormatted
  if os.path.isfile(AllDataFilename):
    if os.path.getsize(AllDataFilename) > 8:
      with open(AllDataFilename, 'r') as AllDataFile:
        LatestRecordFormatted = loads(AllDataFile.read())[0]
      try:
        DateOfCurrentData = LatestRecordFormatted["Date"]
        CurrentDisplay[1] = "{:,}".format(LatestRecordFormatted["Cases"]["New"]).rjust(10) + "|" + "{:,}".format(LatestRecordFormatted["Deaths"]["New"]).rjust(9)
        CurrentDisplay[2] = "{:,}".format(LatestRecordFormatted["Cases"]["Total"]).rjust(10) + "|" + "{:,}".format(LatestRecordFormatted["Deaths"]["Total"]).rjust(9)
        CurrentDisplay[3] = "{:,}".format(LatestRecordFormatted["Cases"]["Corrections"]).rjust(10) + "|" + "{:,}".format(LatestRecordFormatted["Deaths"]["Corrections"]).rjust(9)
        WriteLastDisplay()
      except:
        PrintError()
        ErrorMode = True
        ErrorLED.on()
        DateOfCurrentData = "1970-01-01"
        CurrentDisplay[1] = "X"
        CurrentDisplay[2] = "Previous data found,".center(20)
        CurrentDisplay[3] = "Data is invalid.".center(20)
        WriteLastDisplay()
    else:
      WriteToMainLog("No previous data found.")
      CurrentDisplay[2] = "No previous".center(20)
      CurrentDisplay[3] = "data found.".center(20)
  else:
    WriteToMainLog("No previous data found.")
    CurrentDisplay[2] = "No previous".center(20)
    CurrentDisplay[3] = "data found.".center(20)
  CommitDisplay(CurrentDisplay)

def LoadDiscordInfo():
  global BotToken, ChannelID
  if os.path.isfile(DiscordInfoFilename):
    if os.path.getsize(DiscordInfoFilename) > 8:
      with open(DiscordInfoFilename, 'r') as DiscordInfoFile:
        FileOutput = DiscordInfoFile.read().split('\n')
      for i in range(len(FileOutput)):
        if FileOutput[i].split('=')[0] == "Token":
          BotToken = FileOutput[i].split('=')[1]
        elif FileOutput[i].split('=')[0] == "ID":
          ChannelID = int(FileOutput[i].split('=')[1])
    else:
      raise Exception("Discord bot file invalid.")
  else:
    raise Exception("Discord bot file not found.")

# Common Procedures
async def TimeReview():
  try:
    global BlueBannersWebAddresses, DataAggregationTemplate, LatestRecordFormatted, LogFilename, PrimaryUpdated, SecondaryUpdated, RuntimeLogsRootFolder
    await WaitForDiscord()
    await DiscordClient.change_presence(status=discord.Status.idle)
    WriteToMainLog("Beginning time loop.")
    while True:
      CurrentTime = datetime.now().strftime("%H%M")
      Minutes = datetime.now().strftime("%M")
      if DateOfCurrentData == date.today().isoformat() and not PrimaryUpdated:
        PrimaryUpdated = True
        WriteToMainLog("Latest data confirmed.")
        NewLED.on()
      elif CurrentTime >= BeginTime and not (PrimaryUpdated or SecondaryUpdated):
        WriteToMainLog("API refresh starting.")
        LatestRecordFormatted = DataAggregationTemplate
        await APICheck()
        WriteToMainLog("API refresh ending.")
        if PrimaryUpdated:
          await CheckRollAvgPeaks()
        await asyncio.sleep(90)
        await CheckForMessage()
      elif CurrentTime < BeginTime and PrimaryUpdated:
        LogFilename = RuntimeLogsRootFolder + "Log_" + date.today().isoformat() + ".txt"
        WriteToMainLog("--- NEW DAY ---", False)
        PrimaryUpdated = False
        if SecondaryUpdated:
          SecondaryUpdated = False
        OldLED.off()
        NewLED.off()
        LatestRecordFormatted = DataAggregationTemplate
        BlueBannersWebAddresses = [
          BlueBannersTemplateAddress + date.today().isoformat() + "/Cases/overview/United%20Kingdom",
          BlueBannersTemplateAddress + date.today().isoformat() + "/Deaths/overview/United%20Kingdom",
          BlueBannersTemplateAddress + date.today().isoformat() + "/Vaccinations/overview/United%20Kingdom"
        ]
      elif Minutes == "00":
        await CheckForMessage()
        await asyncio.sleep(55)
      await asyncio.sleep(5)
  except:
    await FatalException()

async def APICheck():
  global CurrentDisplay, DateOfCurrentData, DelayTime, ErrorMode, LatestRecordFormatted, PrimaryUpdated, SecondaryUpdated
  await WaitForDiscord()
  await DiscordClient.change_presence(status=discord.Status.online)
  CurrentDate = date.today().isoformat()
  PreviousDate = (datetime.today() - timedelta(days=1)).isoformat().split('T')[0]
  CurrentTime = datetime.today().strftime("%H%M")
  Minutes = datetime.today().strftime("%M")
  OldLED.on()
  MessagesChecked = False
  while not (PrimaryUpdated and SecondaryUpdated) and CurrentTime != TimeoutCondition:
    CurrentTime = datetime.today().strftime("%H%M")
    Minutes = datetime.today().strftime("%M")
    if int(Minutes) % 15 == 0:
      if not MessagesChecked:
        await CheckForMessage(CurrentDate)
        MessagesChecked = True
    else:
      MessagesChecked = False
    if not PrimaryUpdated:
      try:
        PrimaryUpdated = await PrimaryAPICheck(CurrentDate)
        if ErrorMode:
          if not PrimaryUpdated:
            OldLED.on()
          ErrorMode = False
          ErrorLED.off()
      except:
        if not ErrorMode:
          ErrorMode = True
          OldLED.off()
          NewLED.off()
          ErrorLED.on()
        PrintError()
    if not SecondaryUpdated:
      try:
        SecondaryUpdated = await SecondaryAPICheck(PreviousDate)
      except:
        PrintError()
    if not (PrimaryUpdated and SecondaryUpdated):
      await asyncio.sleep(DelayTime)
  if CurrentTime == TimeoutCondition and not (PrimaryUpdated or SecondaryUpdated):
    ErrorMode = True
    ErrorLED.on()
    if not PrimaryUpdated:  
      OldLED.off()
      CurrentDate = "1970-01-01"
      NewOutput = CurrentDisplay[0:4]
      NewOutput[1] = "NO".center(20)
      NewOutput[2] = "DATA".center(20)
      NewOutput[3] = "TODAY".center(20)
      WriteToMainLog("No data found. Committing to display.")
      CommitDisplay(NewOutput)
      CurrentDisplay = NewOutput[0:4]
    await SendMessage(CurrentDate, "No data was found for this day. Timed out.")
  await DiscordClient.change_presence(status=discord.Status.idle)

async def PrimaryAPICheck(Date):
  global CurrentDisplay, DateOfCurrentData, LatestRecordFormatted
  NewDisplay = CurrentDisplay[0:4]
  WriteToMainLog("Updating primary. . .")
  LastRecord = APIRequest("PRIMARY")
  WriteToMainLog("Updated primary.")
  Latest = False
  if LastRecord["Date"] == Date:
    WriteToMainLog("Verifying all primary metrics exist. . .")
    if VerifyDataExists("PRIMARY", LastRecord):
      WriteToMainLog("Primary verification passed.")
      if LastRecord["Date"] == Date:
        ParseData(LastRecord)
        NewDisplay[1] = "{:,}".format(LatestRecordFormatted["Cases"]["New"]).rjust(10) + "|" + "{:,}".format(LatestRecordFormatted["Deaths"]["New"]).rjust(9)
        NewDisplay[2] = "{:,}".format(LatestRecordFormatted["Cases"]["Total"]).rjust(10) + "|" + "{:,}".format(LatestRecordFormatted["Deaths"]["Total"]).rjust(9)
        NewDisplay[3] = ""
        if LatestRecordFormatted["Cases"]["Corrections"] != None:
          NewDisplay[3] += "{:,}".format(LatestRecordFormatted["Cases"]["Corrections"]).rjust(10) + "|"
        else:
          NewDisplay[3] += "None".rjust(10) + "|"
        if LatestRecordFormatted["Deaths"]["Corrections"] != None:
          NewDisplay[3] += "{:,}".format(LatestRecordFormatted["Deaths"]["Corrections"]).rjust(9)
        else:
          NewDisplay[3] += "None".rjust(9)
        CommitDisplay(NewDisplay)
        OldLED.off()
        NewLED.on()
        WriteLastDisplay()
        await SendData("PRIMARY", LatestRecordFormatted)
        Latest = True
        AddToAllData()
      else:
        DateOfCurrentData = LastRecord["Date"]
        NewDisplay[1] = "{:,}".format(LastRecord["CasesNew"]).rjust(10) + "|" + "{:,}".format(LastRecord["DeathsNew"]).rjust(9)
        NewDisplay[2] = "{:,}".format(LastRecord["CasesTotal"]).rjust(10) + "|" + "{:,}".format(LastRecord["DeathsTotal"]).rjust(9)
        CommitDisplay(NewDisplay)
        WriteLastDisplay()
    else:
      WriteToMainLog("Primary verification failed.")
  return Latest

async def SecondaryAPICheck(Date):
  WriteToMainLog("Updating secondary. . .")
  LastRecord = APIRequest("SECONDARY")
  WriteToMainLog("Updated secondary.")
  Latest = False
  if LastRecord["Date"] == Date:
    WriteToMainLog("Verifying all secondary metrics exist. . .")
    if VerifyDataExists("SECONDARY", LastRecord):
      WriteToMainLog("Secondary verification passed.")
      await SendData("SECONDARY", LastRecord)
      Latest = True
    else:
      WriteToMainLog("Secondary verification failed.")
  return Latest

def APIRequest(Structure):
  if Structure.upper() == "PRIMARY":
    return PrimaryAPI.get_json()["data"][0]
  else:
    return SecondaryAPI.get_json()["data"][0]

def VerifyDataExists(Structure, Data):
  if Structure.upper() == "PRIMARY":
    if type(Data["Date"]) is str:
      if type(Data["CasesNew"]) is int:
        if type(Data["DeathsNew"]) is int:
          if type(Data["CasesTotal"]) is int:
            if type(Data["DeathsTotal"]) is int:
              return True
    return False
  elif Structure.upper() == "SECONDARY":
    if type(Data["Date"]) is str:
      if type(Data["VaccinationsFirstDoseNew"]) is int:
        if type(Data["VaccinationsFirstDoseTotal"]) is int:
          if type(Data["VaccinationsSecondDoseNew"]) is int:
            if type(Data["VaccinationsSecondDoseTotal"]) is int:
              return True
    return False

# Mass Data Handling Procedures
def ParseData(Data):
  global LatestRecordFormatted
  WriteToMainLog("Parsing primary data. . .")
  LatestRecordFormatted["Date"] = Data["Date"]
  LatestRecordFormatted["Day"] = datetime.strptime(Data["Date"], "%Y-%m-%d").weekday()
  LatestRecordFormatted["Cases"]["New"] = Data["CasesNew"]
  LatestRecordFormatted["Deaths"]["New"] = Data["DeathsNew"]
  LatestRecordFormatted["Cases"]["Total"] = Data["CasesTotal"]
  LatestRecordFormatted["Deaths"]["Total"] = Data["DeathsTotal"]
  LatestRecordFormatted["CaseFatality"]["Rate"] = Data["DeathsTotal"] / Data["CasesTotal"]
  AllData = GetAllData()
  if AllData[0]["CaseFatality"]["Rate"] != None:
    LatestRecordFormatted["CaseFatality"]["Change"] = LatestRecordFormatted["CaseFatality"]["Rate"] - AllData[0]["CaseFatality"]["Rate"]
  if AllData[0]["Cases"]["New"] != None:
    LatestRecordFormatted["Cases"]["Change"] = Data["CasesNew"] - AllData[0]["Cases"]["New"]
    if AllData[0]["Cases"]["Total"] != None:
      LatestRecordFormatted["Cases"]["Corrections"] = Data["CasesTotal"] - (Data["CasesNew"] + AllData[0]["Cases"]["Total"])
  if AllData[0]["Deaths"]["New"] != None:
    LatestRecordFormatted["Deaths"]["Change"] = Data["DeathsNew"] - AllData[0]["Deaths"]["New"]
    if AllData[0]["Deaths"]["Total"] != None:
      LatestRecordFormatted["Deaths"]["Corrections"] = Data["DeathsTotal"] - (Data["DeathsNew"] + AllData[0]["Deaths"]["Total"])
  CalculateRollingAverages(3, AllData, Data)
  CalculateRollingAverages(7, AllData, Data)
  WriteToMainLog("Done.")

def GetAllData():
  with open(AllDataFilename, 'r') as AllDataFile:
    AllData = loads(AllDataFile.read())
  return AllData

def CalculateRollingAverages(NumOfDays, AllData, NewData):
  WriteToMainLog("Calculating Rolling Average of length " + str(NumOfDays))
  if NumOfDays == 3:
    RollingAverageLength = "Three"
  else:
    RollingAverageLength = "Seven"
  CasesRollingAverage = NewData["CasesNew"]
  DeathsRollingAverage = NewData["DeathsNew"]
  for i in range(NumOfDays - 1):
    if CasesRollingAverage != None:
      if AllData[i]["Cases"]["New"] != None:
        CasesRollingAverage += AllData[i]["Cases"]["New"]
      else:
        CasesRollingAverage = None
    if DeathsRollingAverage != None:
      if AllData[i]["Deaths"]["New"] != None:
        DeathsRollingAverage += AllData[i]["Deaths"]["New"]
      else:
        DeathsRollingAverage = None
  if CasesRollingAverage != None:
    CasesRollingAverage /= NumOfDays
    LatestRecordFormatted["Cases"]["RollingAverages"][RollingAverageLength]["Average"] = CasesRollingAverage
    if AllData[0]["Cases"]["RollingAverages"][RollingAverageLength]["Average"] != None:
      LatestRecordFormatted["Cases"]["RollingAverages"][RollingAverageLength]["Change"] = CasesRollingAverage - AllData[0]["Cases"]["RollingAverages"][RollingAverageLength]["Average"]
  if DeathsRollingAverage != None:
    DeathsRollingAverage /= NumOfDays
    LatestRecordFormatted["Deaths"]["RollingAverages"][RollingAverageLength]["Average"] = DeathsRollingAverage
    if AllData[0]["Deaths"]["RollingAverages"][RollingAverageLength]["Average"] != None:
      LatestRecordFormatted["Deaths"]["RollingAverages"][RollingAverageLength]["Change"] = DeathsRollingAverage - AllData[0]["Deaths"]["RollingAverages"][RollingAverageLength]["Average"]

def AddToAllData():
  global LatestRecordFormatted
  ExistingData = GetAllData()
  WriteToMainLog("Adding to all data record. . .")
  if ExistingData[0]["Date"] == LatestRecordFormatted["Date"]:
    WriteToMainLog("Latest record already exists in file.")
  else:
    with open(AllDataFilename, 'w') as AllDataFile:
      AllDataFile.write("[\n")
      Output = "  " + dumps(LatestRecordFormatted) + ",\n"
      AllDataFile.write(Output)
      for i in range(len(ExistingData)):
        Output = "  " + dumps(ExistingData[i])
        if i != len(ExistingData) - 1:
          Output += ",\n"
        AllDataFile.write(Output)
      AllDataFile.write("\n]")
  WriteToMainLog("Done.")

async def CheckRollAvgPeaks():
  global LatestRecordFormatted
  WriteToMainLog("Checking rolling average peaks. . .")
  with open(RollAvgPeaksFilename, 'r') as RollAvgPeaksFile:
    RollAvgPeaks = loads(RollAvgPeaksFile.read())
  ChangesMade = False
  CasesRAPeak = False
  DeathsRAPeak = False
  Output = ""
  MessagesTemplate = {
    "Cases": {
      "PeakLocal": "New local RA(7, 'C') peak.",
      "PeakGlobal": "New global RA(7, 'C') peak.",
      "LocalCreated": "New local RA(7, 'C') record created.",
      "GlobalCreated": "New global RA(7 ,'C') record created.",
      "LocalExpired": "Local RA(7, 'C') peak expired."
    },
    "Deaths": {
      "PeakLocal": "New local RA(7, 'D') peak.",
      "PeakGlobal": "New global RA(7, 'D') peak.",
      "LocalCreated": "New local RA(7, 'D') record created.",
      "GlobalCreated": "New global RA(7 ,'D') record created.",
      "LocalExpired": "Local RA(7, 'D') peak expired."
    }
  }
  if type(RollAvgPeaks["Cases"]["Global"]["Value"]) is float:
    if LatestRecordFormatted["Cases"]["RollingAverages"]["Seven"]["Average"] > RollAvgPeaks["Cases"]["Global"]["Value"]:
      ChangesMade = True
      CasesRAPeak = True
      if Output != "":
        Output += "\n"
      Output += MessagesTemplate["Cases"]["PeakGlobal"]
      RollAvgPeaks["Cases"]["Global"]["Date"] = LatestRecordFormatted["Date"]
      RollAvgPeaks["Cases"]["Global"]["Value"] = LatestRecordFormatted["Cases"]["RollingAverages"]["Seven"]["Average"]
      RollAvgPeaks["Cases"]["Local"]["Date"] = LatestRecordFormatted["Date"]
      RollAvgPeaks["Cases"]["Local"]["Value"] = LatestRecordFormatted["Cases"]["RollingAverages"]["Seven"]["Average"]
  else:
    ChangesMade = True
    CasesRAPeak = True
    if Output != "":
      Output += "\n"
    Output += MessagesTemplate["Cases"]["GlobalCreated"] + "\n" + MessagesTemplate["Cases"]["PeakGlobal"]
    RollAvgPeaks["Cases"]["Global"]["Date"] = LatestRecordFormatted["Date"]
    RollAvgPeaks["Cases"]["Global"]["Value"] = LatestRecordFormatted["Cases"]["RollingAverages"]["Seven"]["Average"]
    RollAvgPeaks["Cases"]["Local"]["Date"] = LatestRecordFormatted["Date"]
    RollAvgPeaks["Cases"]["Local"]["Value"] = LatestRecordFormatted["Cases"]["RollingAverages"]["Seven"]["Average"]
  if RollAvgPeaks["Cases"]["Local"]["Value"] == None:
    if LatestRecordFormatted["Cases"]["RollingAverages"]["Seven"]["Change"] > 0:
      AllData = GetAllData()
      NumPositives = 1
      while AllData[NumPositives]["Cases"]["RollingAverages"]["Seven"]["Change"] > 0:
        NumPositives += 1
      if NumPositives >= 7:
        if Output != "":
          Output += "\n"
        Output += MessagesTemplate["Cases"]["LocalCreated"] + "\n" + MessagesTemplate["Cases"]["PeakLocal"]
        ChangesMade = True
        CasesRAPeak = True
        RollAvgPeaks["Cases"]["Local"]["Date"] = LatestRecordFormatted["Date"]
        RollAvgPeaks["Cases"]["Local"]["Value"] = LatestRecordFormatted["Cases"]["RollingAverages"]["Seven"]["Average"]
  if not CasesRAPeak and type(RollAvgPeaks["Cases"]["Local"]["Value"]) is float:
    if LatestRecordFormatted["Cases"]["RollingAverages"]["Seven"]["Average"] > RollAvgPeaks["Cases"]["Local"]["Value"]:
      ChangesMade = True
      CasesRAPeak = True
      if Output != "":
        Output += "\n"
      Output += MessagesTemplate["Cases"]["PeakLocal"]
      RollAvgPeaks["Cases"]["Local"]["Date"] = LatestRecordFormatted["Date"]
      RollAvgPeaks["Cases"]["Local"]["Value"] = LatestRecordFormatted["Cases"]["RollingAverages"]["Seven"]["Average"]
  if type(RollAvgPeaks["Deaths"]["Global"]["Value"]) is float:
    if LatestRecordFormatted["Deaths"]["RollingAverages"]["Seven"]["Average"] > RollAvgPeaks["Deaths"]["Global"]["Value"]:
      ChangesMade = True
      DeathsRAPeak = True
      if Output != "":
        Output += "\n"
      Output += MessagesTemplate["Deaths"]["PeakGlobal"]
      RollAvgPeaks["Deaths"]["Global"]["Date"] = LatestRecordFormatted["Date"]
      RollAvgPeaks["Deaths"]["Global"]["Value"] = LatestRecordFormatted["Deaths"]["RollingAverages"]["Seven"]["Average"]
      RollAvgPeaks["Deaths"]["Local"]["Date"] = LatestRecordFormatted["Date"]
      RollAvgPeaks["Deaths"]["Local"]["Value"] = LatestRecordFormatted["Deaths"]["RollingAverages"]["Seven"]["Average"]
  else:
    ChangesMade = True
    DeathsRAPeak = True
    if Output != "":
      Output += "\n"
    Output += MessagesTemplate["Deaths"]["GlobalCreated"] + "\n" + MessagesTemplate["Deaths"]["PeakGlobal"]
    RollAvgPeaks["Deaths"]["Global"]["Date"] = LatestRecordFormatted["Date"]
    RollAvgPeaks["Deaths"]["Global"]["Value"] = LatestRecordFormatted["Deaths"]["RollingAverages"]["Seven"]["Average"]
    RollAvgPeaks["Deaths"]["Local"]["Date"] = LatestRecordFormatted["Date"]
    RollAvgPeaks["Deaths"]["Local"]["Value"] = LatestRecordFormatted["Deaths"]["RollingAverages"]["Seven"]["Average"]
  if RollAvgPeaks["Deaths"]["Local"]["Value"] == None:
    if LatestRecordFormatted["Deaths"]["RollingAverages"]["Seven"]["Change"] > 0:
      AllData = GetAllData()
      NumPositives = 1
      while AllData[NumPositives]["Deaths"]["RollingAverages"]["Seven"]["Change"] > 0:
        NumPositives += 1
      if NumPositives >= 7:
        if Output != "":
          Output += "\n"
        Output += MessagesTemplate["Deaths"]["LocalCreated"] + "\n" + MessagesTemplate["Deaths"]["PeakLocal"]
        ChangesMade = True
        DeathsRAPeak = True
        RollAvgPeaks["Deaths"]["Local"]["Date"] = LatestRecordFormatted["Date"]
        RollAvgPeaks["Deaths"]["Local"]["Value"] = LatestRecordFormatted["Deaths"]["RollingAverages"]["Seven"]["Average"]
  if not DeathsRAPeak and type(RollAvgPeaks["Deaths"]["Local"]["Value"]) is float:
    if LatestRecordFormatted["Deaths"]["RollingAverages"]["Seven"]["Average"] > RollAvgPeaks["Deaths"]["Local"]["Value"]:
      ChangesMade = True
      DeathsRAPeak = True
      if Output != "":
        Output += "\n"
      Output += MessagesTemplate["Deaths"]["PeakLocal"]
      RollAvgPeaks["Deaths"]["Local"]["Date"] = LatestRecordFormatted["Date"]
      RollAvgPeaks["Deaths"]["Local"]["Value"] = LatestRecordFormatted["Deaths"]["RollingAverages"]["Seven"]["Average"]
  if not CasesRAPeak and RollAvgPeaks["Cases"]["Local"]["Date"] != None:
    if LatestRecordFormatted["Cases"]["RollingAverages"]["Seven"]["Change"] < 0:
      DateOfLastLocal = datetime.strptime(RollAvgPeaks["Cases"]["Local"]["Date"], "%Y-%m-%d")
      CurrentDate = datetime.strptime(LatestRecordFormatted["Date"], "%Y-%m-%d")
      if CurrentDate - DateOfLastLocal >= timedelta(days=10):
        AllData = GetAllData()
        NumNegatives = 1
        while AllData[NumNegatives]["Cases"]["RollingAverages"]["Seven"]["Change"] < 0:
          NumNegatives += 1
        if NumNegatives >= 10:
          ChangesMade = True
          RollAvgPeaks["Cases"]["Local"]["Date"] = None
          RollAvgPeaks["Cases"]["Local"]["Value"] = None
          if Output != "":
            Output += "\n"
          Output += MessagesTemplate["Cases"]["LocalExpired"]
  if not DeathsRAPeak and RollAvgPeaks["Deaths"]["Local"]["Date"] != None:
    if LatestRecordFormatted["Deaths"]["RollingAverages"]["Seven"]["Change"] < 0:
      DateOfLastLocal = datetime.strptime(RollAvgPeaks["Deaths"]["Local"]["Date"], "%Y-%m-%d")
      CurrentDate = datetime.strptime(LatestRecordFormatted["Date"], "%Y-%m-%d")
      if CurrentDate - DateOfLastLocal >= timedelta(days=10):
        AllData = GetAllData()
        NumNegatives = 1
        while AllData[NumNegatives]["Deaths"]["RollingAverages"]["Seven"]["Change"] < 0:
          NumNegatives += 1
        if NumNegatives >= 10:
          ChangesMade = True
          RollAvgPeaks["Deaths"]["Local"]["Date"] = None
          RollAvgPeaks["Deaths"]["Local"]["Value"] = None
          if Output != "":
            Output += "\n"
          Output += MessagesTemplate["Deaths"]["LocalExpired"]
  if ChangesMade:
    with open(RollAvgPeaksFilename, 'w') as RollAvgPeaksFile:
      RollAvgPeaksFile.write("{\n")
      RollAvgPeaksFile.write("  \"Cases\": " + dumps(RollAvgPeaks["Cases"]) + ",\n")
      RollAvgPeaksFile.write("  \"Deaths\": " + dumps(RollAvgPeaks["Deaths"]))
      RollAvgPeaksFile.write("\n}")
  if Output == "":
    Output = "No peaks today."
  await SendNotification(Output)
  WriteToMainLog("Done.")

def FindLastHighest(AllData, CheckData, Metric, StartingIndex = 0):
  LastHighestDate = "#N/A; all time highest"
  if Metric == "CASES":
    if type(CheckData["Cases"]["New"]) is int:
      for i in range(StartingIndex, len(AllData)):
        CurrentIndex = AllData[i]
        if type(CurrentIndex["Cases"]["New"]) is int:
          if CurrentIndex["Cases"]["New"] > CheckData["Cases"]["New"]:
            LastHighestDate = CurrentIndex["Date"] + "; " + "{:,}".format(CurrentIndex["Cases"]["New"])
            break
    else:
      LastHighestDate = "None"
  if Metric == "DEATHS":
    if type(CheckData["Deaths"]["New"]) is int:
      for i in range(StartingIndex, len(AllData)):
        CurrentIndex = AllData[i]
        if type(CurrentIndex["Deaths"]["New"]) is int:
          if CurrentIndex["Deaths"]["New"] > CheckData["Deaths"]["New"]:
            LastHighestDate = CurrentIndex["Date"] + "; " + "{:,}".format(CurrentIndex["Deaths"]["New"])
            break
    else:
      LastHighestDate = "None"
  return LastHighestDate

def GetArrow(Value):
  UpArrow = '\u2B06'
  RightArrow = '\u27A1'
  DownArrow = '\u2B07'
  Output = " "
  if Value == 0:
    Output += RightArrow
  elif Value > 0:
    Output += UpArrow
  elif Value < 0:
    Output += DownArrow
  return Output

# COVID Pi Procedures
def CommitDisplay(NewDisplay):
  global CurrentDisplay
  Display.lcd_clear()
  for i in range(len(NewDisplay)):
    if NewDisplay[i] != "X":
      Display.lcd_display_string(NewDisplay[i], i+1)
  WriteToMainLog("Display refreshed.")
  CurrentDisplay = NewDisplay[0:4]

def WriteLastDisplay():
  global ErrorMode
  with open(LastOutputFilename, 'w') as LastOutputFile:
    LastOutputFile.write(LatestRecordFormatted["Date"] + "," + str(ErrorMode) + "\n")
    for i in range(len(CurrentDisplay)):
      LastOutputFile.write(CurrentDisplay[i] + "\n")
  WriteToMainLog("Current output written to file.")

# Discord Procedures
@DiscordClient.event
async def on_ready():
  WriteToMainLog("We have logged in as {0.user}".format(DiscordClient))

@DiscordClient.event
async def on_message(Message):
  try:
    if Message.channel == DiscordClient.get_channel(id=ChannelID) and len(Message.content) > 0:
      if Message.content[0] == "$":
        WriteToMainLog("Command received.")
        if Message.content.upper().startswith("$GETDATA"):
          Command = Message.content.split(' ')
          if len(Command) == 2:
            if VerifyDate(Command[1]):
              WriteToMainLog("Data requested for " + Command[1])
              AllData = GetAllData()
              DataFound = False
              for i in range(len(AllData)):
                if AllData[i]["Date"] == Command[1]:
                  DataFound = True
                  await SendData("PRIMARY", AllData[i], i)
                  break
              if not DataFound:
                await Message.channel.send("No data was found for that day.")
            elif Command[1] == "latest":
              WriteToMainLog("Latest data requested.")
              AllData = GetAllData()
              await SendData("PRIMARY", AllData[0])
            else:
              await Message.channel.send("`$getdata` command supports date only in ISO 8601 format or \"latest\" for latest data.")
          else:
            await Message.channel.send("`$getdata` command takes exactly one argument.")
        elif Message.content.upper().startswith("$MESSAGES"):
          if not await CheckForMessage(IgnoreSent=True):
            await Message.channel.send("No messages for today yet.")
        elif Message.content.upper().startswith("$RAVGPEAKS"):
          Command = Message.content.split(' ')
          Output = "```"
          if len(Command) <= 3:
            with open(RollAvgPeaksFilename, 'r') as RollAvgPeaksFile:
              RollAvgPeaks = loads(RollAvgPeaksFile.read())
          if len(Command) == 1:
            Output += "\nRolling Average Peaks (7-Day):"
            Output += "\n  Cases:"
            Output += "\n    Local:"
            Output += "\n      Average: {:,}".format(round(RollAvgPeaks["Cases"]["Local"]["Value"], 3))
            Output += "\n      Date:    " + RollAvgPeaks["Cases"]["Local"]["Date"]
            Output += "\n    Global:"
            Output += "\n      Average: {:,}".format(round(RollAvgPeaks["Cases"]["Global"]["Value"], 3))
            Output += "\n      Date:    " + RollAvgPeaks["Cases"]["Global"]["Date"]
            Output += "\n  Deaths:"
            Output += "\n    Local:"
            Output += "\n      Average: {:,}".format(round(RollAvgPeaks["Deaths"]["Local"]["Value"], 3))
            Output += "\n      Date:    " + RollAvgPeaks["Deaths"]["Local"]["Date"]
            Output += "\n    Global:"
            Output += "\n      Average: {:,}".format(round(RollAvgPeaks["Deaths"]["Global"]["Value"], 3))
            Output += "\n      Date:    " + RollAvgPeaks["Deaths"]["Global"]["Date"]
          elif len(Command) == 2:
            if Command[1].upper() == "CASES":
              Output += "\nCases Rolling Average Peaks (7-Day):"
              Output += "\n  Local:"
              Output += "\n    Average: {:,}".format(round(RollAvgPeaks["Cases"]["Local"]["Value"], 3))
              Output += "\n    Date:    " + RollAvgPeaks["Cases"]["Local"]["Date"]
              Output += "\n  Global:"
              Output += "\n    Average: {:,}".format(round(RollAvgPeaks["Cases"]["Global"]["Value"], 3))
              Output += "\n    Date:    " + RollAvgPeaks["Cases"]["Global"]["Date"]
            elif Command[1].upper() == "DEATHS":
              Output += "\nDeaths Rolling Average Peaks (7-Day):"
              Output += "\n  Local:"
              Output += "\n    Average: {:,}".format(round(RollAvgPeaks["Deaths"]["Local"]["Value"], 3))
              Output += "\n    Date:    " + RollAvgPeaks["Deaths"]["Local"]["Date"]
              Output += "\n  Global:"
              Output += "\n    Average: {:,}".format(round(RollAvgPeaks["Deaths"]["Global"]["Value"], 3))
              Output += "\n    Date:    " + RollAvgPeaks["Deaths"]["Global"]["Date"]
            elif Command[1].upper() == "HELP":
              Output += "\nCommand format: $ravgpeaks [Metric] [Length]"
              Output += "\nMetric and Length parameters are optional.\n"
              Output += "\nValid inputs for Metric:"
              Output += "\n  Cases: return rolling average peaks for cases."
              Output += "\n  Deaths: return rolling average peaks for deaths.\n"
              Output += "\nValid inputs for Length:"
              Output += "\n  Local: returns the current local peak, or none if no peak."
              Output += "\n  Global: returns the current all-time global peak, or none if no peak."
            else:
              Output = "Invalid metric: " + Command[1]
          elif len(Command) == 3:
            if Command[1].upper() == "CASES":
              if Command[2].upper() == "LOCAL":
                Output += "\nCases Local Rolling Average Peaks (7-Day):"
                Output += "\n  Average: {:,}".format(round(RollAvgPeaks["Cases"]["Local"]["Value"], 3))
                Output += "\n  Date:    " + RollAvgPeaks["Cases"]["Local"]["Date"]
              elif Command[2].upper() == "GLOBAL":
                Output += "\nCases Global Rolling Average Peaks (7-Day):"
                Output += "\n  Average: {:,}".format(round(RollAvgPeaks["Cases"]["Global"]["Value"], 3))
                Output += "\n  Date:    " + RollAvgPeaks["Cases"]["Global"]["Date"]
              else:
                Output = "Invalid length: " + Command[2]
            elif Command[1].upper() == "DEATHS":
              if Command[2].upper() == "LOCAL":
                Output += "\nDeaths Local Rolling Average Peaks (7-Day):"
                Output += "\n  Average: {:,}".format(round(RollAvgPeaks["Deaths"]["Local"]["Value"], 3))
                Output += "\n  Date:    " + RollAvgPeaks["Deaths"]["Local"]["Date"]
              elif Command[2].upper() == "GLOBAL":
                Output += "\nDeaths Global Rolling Average Peaks (7-Day):"
                Output += "\n  Average: {:,}".format(round(RollAvgPeaks["Deaths"]["Global"]["Value"], 3))
                Output += "\n  Date:    " + RollAvgPeaks["Deaths"]["Global"]["Date"]
              else:
                Output = "Invalid length: " + Command[2]
            else:
              Output = "Invalid metric: " + Command[1]
          if Output.split('\n')[0] == "```":
            Output += "\n\nThe bot will create a new local peak after 7 consecutive days of positive average change and will expire a local peak after 10 consecutive days of negative average change."
            Output += "\n```"
          await SendNotification(Output)
        elif Message.content.upper().startswith("$VARIANT"):
          await VariantLookup(Message)
        elif Message.content.upper().startswith("$VERSION"):
          Changelog = [
            "1. API: Changed scan start time from 1540 to 1440 & timeout condition from 1500 to 1400.",
            "2. Secondary: Added total doses delivered as sum of the existing First, Second, and Additional doses.",
            "3. API: Fixed a bug that caused the bot to crash if a timeout condition was reached.",
            "4. Messages: Fixed an error that caused the wrong ISO standard to be displayed in the `$help` prompt.",
            "5. Variants: Fixed a bug that caused the script to crash when using the `number` command."
          ]
          Output = "COVID Pi and ~~UK-COV19 Bot~~ Botty-Mc-Bot-Face Version " + VersionNum + ".\n"
          Output += "Changelog:\n"
          for i in range(len(Changelog)):
            Output += "  " + Changelog[i] + "\n"
          await Message.channel.send(Output)
        else:
          Output = ""
          Output += "\nCommand syntax:"
          Output += "\n  $getdata [date/\'latest\']: Returns the primary data from the date specfied"
          Output += "\n    date: A date given in ISO 8601 (YYYY-MM-DD) form."
          Output += "\n    \'latest\': The literal word, returns the latest data available."
          Output += "\n  $messages: Outputs any messages for the current day."
          Output += "\n  $ravgpeaks: Displays the latest rolling average peaks. Refer to $ravgpeaks help."
          Output += "\n  $variant: Returns variant information based on commands specified. Refer to $variant help."
          Output += "\n  $version: Shows current bot version and changelog from previous version."
          await Message.channel.send(Output)
      elif Message.content.lower() == "good bot":
        await Message.channel.send("Much thank")
  except:
    PrintError()
    await SendNotification("Unhandled exception occured when parsing your request. Please pester the bot admin for a solution.")

@DiscordClient.event
async def on_message_edit(BeforeMessage, AfterMessage):
  if BeforeMessage.content != AfterMessage.content:
    await on_message(AfterMessage)

async def WaitForDiscord():
  global ErrorMode
  SuccessfulWait = False
  try:
    while not SuccessfulWait:
      WriteToMainLog("Waiting for discord bot to be ready. . .")
      await DiscordClient.wait_until_ready()
      WriteToMainLog("Done.")
      SuccessfulWait = True
  except:
    PrintError()
    if not ErrorMode:
      ErrorLED.on()
      ErrorMode = True
    await asyncio.sleep(15)
  if ErrorMode:
    ErrorMode = False
    ErrorLED.off()

def VerifyDate(Date):
  try:
    return datetime.strptime(Date, "%Y-%m-%d")
  except ValueError: 
    return False

@DiscordClient.event
async def SendData(Structure, Data, Index = 0):
  await WaitForDiscord()
  WriteToMainLog("Sending Discord message for " + Structure.lower() + " structure. . .")
  Channel = DiscordClient.get_channel(id=ChannelID)
  DateStamp = datetime.now().astimezone().replace(microsecond=0).isoformat(sep='T')
  Weekdays = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday"
  ]
  RedCross = '\u274C'
  CasesDot = '\U0001F535'
  DeathsDot = '\U0001F534'
  CFRDot = '\U0001F7E1'
  SecondaryDot = '\U0001F7E2'
  ShowLastHighest = False
  if os.path.isfile(AllDataFilename):
    AllData = GetAllData()
    ShowLastHighest = True
  Output = "```\n"
  if Structure == "PRIMARY":
    Output += "PRIMARY DATA FOR " + Data["Date"] + ", " + Weekdays[Data["Day"]]
    Output += "\n" + CasesDot + "Cases:"
    CasesData = Data["Cases"]
    if type(CasesData["New"]) is int:
      Output += "\n    New:          {:,}".format(CasesData["New"])
    else:
      Output += "\n    New:          None"
    if type(CasesData["Change"]) is int:
      Output += "\n    Change:       {:,}".format(CasesData["Change"]) + GetArrow(CasesData["Change"])
    else:
      Output += "\n    Change        None" + RedCross
    if ShowLastHighest:
      Output += "\n    Last Highest: " + FindLastHighest(AllData, Data, "CASES", Index)
    else:
      Output += "\n    Last Highest: None"
    Output += "\n    Roll Avg (3-Day):"
    if type(CasesData["RollingAverages"]["Three"]["Average"]) is float:
      Output += "\n      Average:    {:,}".format(round(CasesData["RollingAverages"]["Three"]["Average"], 3))
    else:
      Output += "\n      Average:    None"
    if type(CasesData["RollingAverages"]["Three"]["Change"]) is float:
      Output += "\n      Change:     {:,}".format(round(CasesData["RollingAverages"]["Three"]["Change"], 3)) + GetArrow(CasesData["RollingAverages"]["Three"]["Change"])
    else:
      Output += "\n      Change:     None" + RedCross
    Output += "\n    Roll Avg (7-Day):"
    if type(CasesData["RollingAverages"]["Seven"]["Average"]) is float:
      Output += "\n      Average:    {:,}".format(round(CasesData["RollingAverages"]["Seven"]["Average"], 3))
    else:
      Output += "\n      Average:    None"
    if type(CasesData["RollingAverages"]["Seven"]["Change"]) is float:
      Output += "\n      Change:     {:,}".format(round(CasesData["RollingAverages"]["Seven"]["Change"], 3)) + GetArrow(CasesData["RollingAverages"]["Seven"]["Change"])
    else:
      Output += "\n      Change:     None" + RedCross
    if type(CasesData["Corrections"]) is int:
      Output += "\n    Corrections:  {:,}".format(CasesData["Corrections"])
    else:
      Output += "\n    Corrections:  None"
    if type(CasesData["Total"]) is int:
      Output += "\n    Total:        {:,}".format(CasesData["Total"])
    else:
      Output += "\n    Total:        None"
    Output += "\n" + DeathsDot + "Deaths:"
    DeathsData = Data["Deaths"]
    if type(DeathsData["New"]) is int:
      Output += "\n    New:          {:,}".format(DeathsData["New"])
    else:
      Output += "\n    New:          None"
    if type(DeathsData["Change"]) is int:
      Output += "\n    Change:       {:,}".format(DeathsData["Change"]) + GetArrow(DeathsData["Change"])
    else:
      Output += "\n    Change        None" + RedCross
    if ShowLastHighest:
      Output += "\n    Last Highest: " + FindLastHighest(AllData, Data, "DEATHS", Index)
    else:
      Output += "\n    Last Highest: None"
    Output += "\n    Roll Avg (3-Day):"
    if type(DeathsData["RollingAverages"]["Three"]["Average"]) is float:
      Output += "\n      Average:    {:,}".format(round(DeathsData["RollingAverages"]["Three"]["Average"], 3))
    else:
      Output += "\n      Average:    None"
    if type(DeathsData["RollingAverages"]["Three"]["Change"]) is float:
      Output += "\n      Change:     {:,}".format(round(DeathsData["RollingAverages"]["Three"]["Change"], 3)) + GetArrow(DeathsData["RollingAverages"]["Three"]["Change"])
    else:
      Output += "\n      Change:     None" + RedCross
    Output += "\n    Roll Avg (7-Day):"
    if type(DeathsData["RollingAverages"]["Seven"]["Average"]) is float:
      Output += "\n      Average:    {:,}".format(round(DeathsData["RollingAverages"]["Seven"]["Average"], 3))
    else:
      Output += "\n      Average:    None"
    if type(DeathsData["RollingAverages"]["Seven"]["Change"]) is float:
      Output += "\n      Change:     {:,}".format(round(DeathsData["RollingAverages"]["Seven"]["Change"], 3)) + GetArrow(DeathsData["RollingAverages"]["Seven"]["Change"])
    else:
      Output += "\n      Change:     None" + RedCross
    if type(DeathsData["Corrections"]) is int:
      Output += "\n    Corrections:  {:,}".format(DeathsData["Corrections"])
    else:
      Output += "\n    Corrections:  None"
    if type(DeathsData["Total"]) is int:
      Output += "\n    Total:        {:,}".format(DeathsData["Total"])
    else:
      Output += "\n    Total:        None"
    Output += "\n" + CFRDot + "Case Fatality Rate:"
    CFRData = Data["CaseFatality"]
    if type(CFRData["Rate"]) is float:
      Output += "\n    Rate:         {:,}".format(round(CFRData["Rate"] * 100, 3)) + "%"
    else:
      Output += "\n    Rate:         None"
    if type(CFRData["Change"]) is float:
      Output += "\n    Change:       {:,}".format(round(CFRData["Change"] * 100, 3)) + " p.p." + GetArrow(CFRData["Change"])
    else:
      Output += "\n    Change:       None" + RedCross
  elif Structure == "SECONDARY":
    UKPopulation = 68306137
    Output += SecondaryDot + "SECONDARY DATA FOR " + Data["Date"] + ", " + Weekdays[datetime.strptime(Data["Date"], "%Y-%m-%d").weekday()]
    Output += "\n  UK Population:  {:,}".format(UKPopulation)
    Output += "\n  Vaccinations (First Dose):"
    Output += "\n    New:          {:,}".format(Data["VaccinationsFirstDoseNew"])
    Output += "\n    Total:        {:,}".format(Data["VaccinationsFirstDoseTotal"])
    Output += "\n    % Population: " + str(round((Data["VaccinationsFirstDoseTotal"]/UKPopulation) * 100, 3)) + "%"
    Output += "\n  Vaccinations (Second Dose):"
    Output += "\n    New:          {:,}".format(Data["VaccinationsSecondDoseNew"])
    Output += "\n    Total:        {:,}".format(Data["VaccinationsSecondDoseTotal"])
    Output += "\n    % Population: " + str(round((Data["VaccinationsSecondDoseTotal"]/UKPopulation) * 100, 3)) + "%"
    Output += "\n  Vaccinations (Additional Doses):"
    Output += "\n    New:          {:,}".format(Data["VaccinationsAdditionalDoseNew"])
    Output += "\n    Total:        {:,}".format(Data["VaccinationsAdditionalDoseTotal"])
    Output += "\n    % Population: " + str(round((Data["VaccinationsAdditionalDoseTotal"]/UKPopulation) * 100, 3)) + "%"
    Output += "\n  Vaccinations (Total Doses):"
    Output += "\n    New:          {:,}".format(Data["VaccinationsFirstDoseNew"] + Data["VaccinationsSecondDoseNew"] + Data["VaccinationsAdditionalDoseNew"])
    Output += "\n    Total:        {:,}".format(Data["VaccinationsFirstDoseTotal"] + Data["VaccinationsSecondDoseTotal"] + Data["VaccinationsAdditionalDoseTotal"])
    Output += "\n    % Population: " + str(round((Data["VaccinationsFirstDoseTotal"] + Data["VaccinationsSecondDoseTotal"] + Data["VaccinationsAdditionalDoseTotal"]) / UKPopulation * 100, 3)) + "%"
  Output += "\nObtained at " + DateStamp + "\n```"
  await Channel.send(Output)
  WriteToMainLog("Sent Discord message for " + Structure.lower() + " structure.")

@DiscordClient.event
async def SendNotification(Notification):
  await WaitForDiscord()
  Channel = DiscordClient.get_channel(id=ChannelID)
  await Channel.send(Notification)

# COVID Variant Procedures
async def VariantLookup(Message):
  try:
    Command = Message.content.split(' ')
    if len(Command) == 1 or len(Command) >= 3:
      with open(VariantsFilename, 'r') as VariantsFile:
        Variants = loads(VariantsFile.read())
      await SendNotification("Variants information was last updated on " + Variants["Last Updated"] + ".")
    Output = ""
    VariantFound = False
    if len(Command) == 1:
      VariantFound = True
      VariantsList = Variants["Variants"]
      for i in range(len(VariantsList)):
        Variant = VariantsList[i]
        Output += VariantDetails(VariantsList[i], i + 1)
        if len(Output) + 50 > 2000:
          await SendNotification(Output)
          Output = ""
    elif len(Command) == 2:
      VariantFound = True
      if Command[1].upper() == "HELP":
        Output = "Variant lookup help:\n```"
        Output += "\nCommand Format: $variant [DataType] [IndexTerm]"
        Output += "\nDataType and IndexTerm parameters are both optional – omitting both returns all known variants. However, omitting one but not the other is allowed only to access help."
        Output += "\n"
        Output += "\nValid inputs for DataType:"
        Output += "\n  To search by number: \"number\", \"num\", \"no\"."
        Output += "\n  To search by Greek letter: \"letter\", \"ltr\" (Case-senitive index term)."
        Output += "\n  To search by latin name of Greek letter: \"latin\"."
        Output += "\n  To search by PANGO lineage: \"pango\", \"scientific\", \"sci\"."
        Output += "\n  To search by variant type: \"type\", \"variant\"."
        Output += "\n  To search by earliest sample date: \"date\"."
        Output += "\n  To search by associated country: \"nation\", \"country\"."
        Output += "\n"
        Output += "\nWhere the IndexTerm is not able to find a variant, an appropriate message will be displayed instead."
        Output += "\n```"
      else:
        Output = "Invalid parameter: " + Command[1]
    elif len(Command) >= 3:
      if Command[1].upper() == "NATION" or Command[1].upper() == "COUNTRY":
        try:
          VariantsList = Variants["Variants"]
          Nation = ""
          if len(Command) > 3:
            for i in range(2, len(Command)):
              Nation += Command[i]
              if i != len(Command) - 1:
                Nation += " "
          else:
            Nation = flag.dflagize(Command[2]).replace(":", "")
          if Nation.upper() != "UN":
            Nation = countries.get(Nation).alpha2
          for i in range(len(VariantsList)):
            Variant = VariantsList[i]
            if len(Variant) > 1:
              if Variant["Nation"].upper() == Nation.upper():
                VariantFound = True
                Output += "\n`" + Nation + "` MATCHES VARIANT:"
                Output += VariantDetails(Variant, i + 1)
        except KeyError:
          VariantFound = True
          Output = "Nation not found. This may be due to a typo in the Aplha-2 or Alpha-3 code. Full national names are only partially supported."
      elif len(Command) == 3:
        if Command[1].upper() == "NUMBER" or Command[1].upper() == "NUM" or Command[1].upper() == "NO":
          try:
            if int(Command[2]) < 1:
              raise ValueError()
            Output += "\n`" + Command[2] + "` MATCHES VARIANT:"
            Output = VariantDetails(Variants["Variants"][int(Command[2]) - 1], int(Command[2]))
            VariantFound = True
          except ValueError:
            VariantFound = True
            Output = "Invalid number: " + Command[2]
        elif Command[1].upper() == "LETTER" or Command[1].upper() == "LTR":
          VariantsList = Variants["Variants"]
          for i in range(len(VariantsList)):
            Variant = VariantsList[i]
            if len(Variant) > 1:
              if Variant["Variant of"].upper() == "CONCERN" or Variant["Variant of"].upper() == "INTEREST":
                if Variant["Ltr"] == Command[2]:
                  VariantFound = True
                  Output += "\n`" + Command[2] + "` MATCHES VARIANT:"
                  Output += VariantDetails(Variant, i + 1)
        elif Command[1].upper() == "LATIN":
          VariantsList = Variants["Variants"]
          for i in range(len(VariantsList)):
            Variant = VariantsList[i]
            if len(Variant) > 1:
              if Variant["Variant of"].upper() == "CONCERN" or Variant["Variant of"].upper() == "INTEREST":
                if Variant["Latin"].upper() == Command[2].upper():
                  VariantFound = True
                  Output += "\n`" + Command[2] + "` MATCHES VARIANT:"
                  Output += VariantDetails(Variant, i + 1)
        elif Command[1].upper() == "PANGO" or Command[1].upper() == "SCIENTIFIC" or Command[1].upper() == "SCI":
          AssociationsList = Variants["Associations"]
          VariantsList = Variants["Variants"]
          for i in range(len(AssociationsList)):
            Association = AssociationsList[i]
            if len(Association) > 1:
              Substring = Association["Substring"].upper()
              if Command[2].upper().startswith(Substring.upper()):
                for k in range(len(VariantsList)):
                  Variant = VariantsList[k]
                  for m in range(len(Association["References"])):
                    Reference = Association["References"][m]
                    for o in range(len(Variant["PANGO"])):
                      PANGO = Variant["PANGO"][o]
                      if Reference == PANGO:
                        VariantFound = True
                        Output += "\n`" + Command[2] + "` REFERENCES VARIANT:"
                        Output += VariantDetails(Variant, k + 1)
            if VariantFound:
              break
          if not VariantFound:
            for i in range(len(VariantsList)):
              Variant = VariantsList[i]
              if len(Variant) > 1:
                for k in range(len(Variant["PANGO"])):
                  if Variant["PANGO"][k].upper() == Command[2].upper():
                    VariantFound = True
                    Output += "\n`" + Command[2] + "` MATCHES VARIANT:"
                    Output += VariantDetails(Variant, i + 1)
                    break
              if VariantFound:
                break
        elif Command[1].upper() == "TYPE" or Command[1].upper() == "VARIANT":
          VariantsList = Variants["Variants"]
          for i in range(len(VariantsList)):
            Variant = VariantsList[i]
            if len(Variant) > 1:
              if Variant["Variant of"].upper() == Command[2].upper():
                VariantFound = True
                Output += "\n`" + Command[2] + "` MATCHES VARIANT:"
                Output += VariantDetails(Variant, i + 1)
        elif Command[1].upper() == "DATE":
          try:
            datetime.strptime(Command[2], "%Y-%m")
            VariantsList = Variants["Variants"]
            for i in range(len(VariantsList)):
              Variant = VariantsList[i]
              if len(Variant) > 1:
                if Variant["Earliest Sample"] == Command[2]:
                  VariantFound = True
                  Output += "\n`" + Command[2] + "` MATCHES VARIANT:"
                  Output += VariantDetails(Variant, i + 1)
          except ValueError:
            VariantFound = True
            Output = "Invalid IndexName: " + Command[2] + ". Dates must be in ISO 8601 format YYYY-MM."  
      else:
        VariantFound = True
        Output = "Invalid parameter count: " + str(len(Command)) + ", for DataType: " + Command[1]
    if not VariantFound:
      Output = "No variants found for " + Command[1] + " " + Command[2] + "."
      VariantFound = True
    if Output == "":
      Output = "If you are reading this, something went tits up."
    await SendNotification(Output)
  except:
    PrintError()
    await SendNotification("Unhandled exception occured when parsing your request. Please pester the bot admin for a solution.")

def VariantDetails(VariantData, Number):
  Output = "\n№: " + str(Number)
  if VariantData["Variant of"] == "Concern" or VariantData["Variant of"] == "Interest":
    Output += "\nLetter: " + VariantData["Ltr"]
    Output += "\nLatin Name: " + VariantData["Latin"]
  Output += "\nPango Name(s):"
  for i in range(len(VariantData["PANGO"])):
    Output += " " + VariantData["PANGO"][i]
    if i != len(VariantData["PANGO"]) - 1:
      Output += ","
  Output += "\nVariant of: " + VariantData["Variant of"]
  Output += "\nEarliest Sample: " + VariantData["Earliest Sample"]
  Output += "\nAssociated Nation: " + flag.flag(VariantData["Nation"])
  if VariantData["Nation"].upper() == "UN":
    Output += " Multiple Countries"
  else:
    Output += " " + countries.get(VariantData["Nation"]).name
  return Output

# Status Messages
async def CheckForMessage(CurrentDate = None, IgnoreSent = False):
  if CurrentDate == None:
    CurrentDate = date.today().isoformat()
  try:
    NewMessages = False
    SuccessfulCheck = False
    while not SuccessfulCheck:
      with open(MessagesFilename, 'r') as MessagesFile:
        FileContents = loads(MessagesFile.read())
      try:
        WriteToMainLog("Checking for administrative messages. . .")
        for i in range(len(FileContents)):
          Message = FileContents[i]
          if Message["Type"] == "AdminMessages":
            if Message["Date"] == CurrentDate:
              if not MessageAlreadySent(Message["Message"], FileContents, IgnoreSent):
                NewMessages = True
                await SendMessage(CurrentDate, Message["Message"])
                Message["Sent"] = True
        SuccessfulCheck = True
        WriteToMainLog("Done.")
      except:
        PrintError()
        await asyncio.sleep(5)
    SuccessfulCheck = False
    while not SuccessfulCheck:
      try:
        WriteToMainLog("Checking for log banner (blue) messages. . .")
        for i in range(len(BlueBannersWebAddresses)):
          Request = requests.get(BlueBannersWebAddresses[i])
          Messages = loads(Request.text)
          for k in range(len(Messages)):
            Message = Messages[k]
            if Message["date"] == CurrentDate:
              if Message["type"].upper() == "UPDATE" or Message["type"].upper() == "DATA ISSUE" or Message["type"].upper() == "CHANGE TO METRIC":
                if not MessageAlreadySent(Message["body"], FileContents, IgnoreSent):
                  await SendMessage(CurrentDate, Message["body"])
                  NewMessages = True
                  if not IgnoreSent or not MessageAlreadySent(Message["body"], FileContents, False):
                    FileContents.append(
                      {
                        "Date": CurrentDate,
                        "Message": Message["body"],
                        "Type": "LogBannersMessages",
                        "Sent": True
                      }
                    )
        WriteToMainLog("Done.")
        SuccessfulCheck = True
      except:
        PrintError()
        await asyncio.sleep(5)
    SuccessfulCheck = False
    while not SuccessfulCheck:
      try:
        WriteToMainLog("Checking for announcement (yellow) messages. . .")
        Request = requests.get(YellowBannersWebAddress)
        Messages = loads(Request.text)
        for i in range(len(Messages)):
          Message = Messages[i]
          if Message["date"] == CurrentDate:
            if not MessageAlreadySent(Message["body"], FileContents, IgnoreSent):
              await SendMessage(CurrentDate, Message["body"])
              NewMessages = True
              if not IgnoreSent or not MessageAlreadySent(Message["body"], FileContents, False):
                FileContents.append(
                  {
                    "Date": CurrentDate,
                    "Message": Message["body"],
                    "Type": "Announcements",
                    "Sent": True
                  }
                )
        WriteToMainLog("Done.")
        SuccessfulCheck = True
      except:
        PrintError()
        await asyncio.sleep(5)
    if NewMessages:
      WriteToMainLog("Updating messages file. . .")
      with open(MessagesFilename, 'w') as MessagesFile:
        MessagesFile.write("[\n")
        for i in range(len(FileContents)):
          MessagesFile.write("  " + dumps(FileContents[i]))
          if i != len(FileContents) - 1:
            MessagesFile.write(",\n")
        MessagesFile.write("\n]")
      WriteToMainLog("Done.")
  except:
    PrintError()
  return NewMessages

def MessageAlreadySent(Message, MessagesFileContents, IgnoreSent):
  if IgnoreSent:
    return False
  for i in range(len(MessagesFileContents)):
    if Message == MessagesFileContents[i]["Message"]:
      return MessagesFileContents[i]["Sent"]
  return False

@DiscordClient.event
async def SendMessage(Date, Message):
  WriteToMainLog("Sending message. . .")
  await WaitForDiscord()
  Channel = DiscordClient.get_channel(id=ChannelID)
  Output = "Message for " + Date + ":\n> " + Message.replace("\n", "\n> ")
  await Channel.send(Output)
  WriteToMainLog("Message sent.")

# Log Procedures
def WriteToMainLog(Text, Date = True):
  if Date:
    Output = "[" + datetime.now().astimezone().replace(microsecond=0).isoformat(sep='T') + "] " + Text + "\n"
  else:
    Output = Text + "\n"
  with open(LogFilename, 'a') as LogFile:
    LogFile.write(Output)

def PrintError():
  with open(LogFilename,'a') as LogFile:
    LogFile.write("["+datetime.now().astimezone().replace(microsecond=0).isoformat(sep='T')+"] Critical Error {\n")
    LogFile.write(traceback.format_exc())
    LogFile.write("\n}\n")

async def FatalException(WriteToFile = True):
  ErrorLED.on()
  OldLED.off()
  NewLED.off()
  Display.lcd_clear()
  Display.lcd_display_string("WARNING!".center(20),1)
  Display.lcd_display_string("The script has quit.",2)
  if WriteToFile:
    ErrorLogFilename = ErrorLogsRootFolder + "Error_" + datetime.now().strftime("%Y-%m-%dT%H%M%S") + ".txt"
    with open(ErrorLogFilename,'a') as ErrorFile:
      ErrorFile.write("[" + datetime.now().astimezone().replace(microsecond=0).isoformat(sep='T') + "] Fatal Error (Exception point 1) {\n")
      ErrorFile.write(traceback.format_exc())
      ErrorFile.write("\n}\n")
  else:
    Display.lcd_display_string("File not written.".center(20),4)
  while True:
    ErrorLED.off()
    await asyncio.sleep(0.9)
    ErrorLED.on()
    await asyncio.sleep(0.1)

if __name__ == "__main__":
  try:
    LogFilename += date.today().isoformat() + ".txt"
    if BeginTime < TimeoutCondition:
      raise Exception("Timeout condition is later than start time.")
    WriteToMainLog("Program Run, Version " + VersionNum)
    POST()
    WaitForNetwork()
    ReloadLastOutputFromFile()
    LoadDiscordInfo()
    DiscordClient.loop.create_task(TimeReview())
    DiscordClient.run(BotToken)
  except Exception:
    ErrorLED.on()
    OldLED.off()
    NewLED.off()
    Display.lcd_clear()
    Display.lcd_display_string("WARNING!".center(20),1)
    Display.lcd_display_string("The script has quit.",2)
    ErrorLogFilename = ErrorLogsRootFolder + "Error_" + datetime.now().strftime("%Y-%m-%dT%H%M%S") + ".txt"
    with open(ErrorLogFilename,'a') as ErrorFile:
      ErrorFile.write("[" + datetime.now().astimezone().replace(microsecond=0).isoformat(sep='T') + "] Fatal Error (Exception point 2) {\n")
      ErrorFile.write(traceback.format_exc())
      ErrorFile.write("\n}\n")
  while True:
    ErrorLED.off()
    time.sleep(0.9)
    ErrorLED.on()
    time.sleep(0.1)