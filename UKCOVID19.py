from datetime import date, datetime, timedelta
from pydoc import _OldStyleClass
from unittest.mock import NonCallableMagicMock
from gpiozero import LED
from iso3166 import countries
from json import dumps, loads
from uk_covid19 import Cov19API
import asyncio, discord, flag, lcddriver, os, requests, time, traceback

# Global Constants
Version = "7.0"
BeginTime = ""
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
Metrics = [
  "Cases",
  "Deaths"
]
NetworkTestAddresses = [
  
]
TimeoutTime = "2359"

# COVID API Constants
Filters = [
  "areaType=Overview",
  "areaName=UnitedKingdom"
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
AllDataAPI = Cov19API(Filters, PrimaryStructure)

# COVID Pi GPIO Constants
Display = lcddriver.lcd()
ErrorLED = LED(14)
OldLED = LED(15)
NewLED = LED(18)

# Discord Constants
DiscordClient = discord.Client()
BotToken = ""
ChannelID = 0

# Files
Files = {
  "AllData": None,
  "Config": "config.json",
  "ErrorLogs": "",
  "Messages": "",
  "RollAvgPeaks": "",
  "RuntimeLogs": "",
  "Variants": None
}

# Messages Addresses
StatusMessagesAddresses = {
  "BlueBannersAddresses": [],
  "YellowBannersAddress": None
}

# Global Variables
CurrentDisplay = [
  "Cases".center(10) + "|" + "Deaths".center(9),
  "X",
  "X",
  "X"
]
DateOfCurrentData = "1970-01-01"
ErrorMode = False
ExcludedDates = []
LatestRecordFormatted = loads(dumps(DataAggregationTemplate))
PrimaryUpdated = False
SecondaryUpdated = False
UKPopulation = None
VariantsEnable = False

# Startup Procedures
def POST():
  Display.lcd_clear()
  Display.lcd_display_string("Welcome to COVID Pi.", 1)
  Display.lcd_display_string("Version " + Version + ".", 2)
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

def LoadConfig(Reload = False):
  global BeginTime, BotToken, ChannelID, DelayTime, ExcludedDates, Files, NetworkTestAddresses, TimeoutTime, VariantsEnable
  WriteToMainLog("Loading configuration file. . .")
  if os.path.isfile(Files["Config"]):
    with open(Files["Config"]) as ConfigFile:
      ConfigFileContents = loads(ConfigFile.read())
    WriteToMainLog("File loaded.")
    if ConfigFileContents.has_key("Configuration"):
      WriteToMainLog("Loading general configuration. . .")
      Configuration = ConfigFileContents["Configuration"]
      if Configuration.has_key("ExcludedDates"):
        ExcludedDates = Configuration["ExcludedDates"]
      if not Reload:
        if Configuration.has_key("NetworkTestAddresses"):
          Addresses = Configuration["NetworkTestAddresses"]
          if Addresses.has_key("Internal"):
            NetworkTestAddresses["Internal"] = Addresses["Internal"]
          else:
            raise Exception("Internal network URL or IP address not found in file.")
          if Addresses.has_key("External"):
            NetworkTestAddresses["Enternal"] = Addresses["External"]
          else:
            raise Exception("External network URL or IP address not found in file.")
        else:
          raise Exception("Specified addresses for network test not found in file.")
      if Configuration.has_key("StartSearchingTime"):
        BeginTime = Configuration["StartSearchingTime"]
      else:
        raise Exception("Searching start time not found in file.")
      if Configuration.has_key("TimeoutTime"):
        TimeoutTime = Configuration["TimeoutTime"]
      else:
        WriteToMainLog("Timeout time not found in configuration file. Using default timeout time.")
      if Configuration.has_key("UKPopulation"):
        if type(Configuration["UKPopulation"]) is int:
          UKPopulation = Configuration["UKPopulation"]
        else:
          raise Exception("Key \UKPopulation\" must be in integer data type.")
      else:
        raise Exception("UK Population count not found in file.")
      if Configuration.has_key("VariantsEnable"):
        VariantsEnable = Configuration["VariantsEnable"]
      else:
        WriteToMainLog("Variants toggle not found in file. Using default value.")
      if Configuration.has_key("WaitTime"):
          DelayTime = Configuration["WaitTime"]
      else:
        WriteToMainLog("Wait time not found in file. Using default wait time.")
      WriteToMainLog("General configuration loaded. . .")
    else:
      raise Exception("Configuration settings not found in file.")
    if not Reload:
      if ConfigFileContents.has_key("Discord"):
        WriteToMainLog("Loading Discord configuration. . .")
        DiscordSettings = ConfigFileContents["Discord"]
        if DiscordSettings.has_key("BotToken"):
          BotToken = DiscordSettings["BotToken"]
        else:
          raise Exception("Discord bot token not found in file.")
        if DiscordSettings.has_key("ChannelID"):
          ChannelID = DiscordSettings["ChannelID"]
        else:
          raise Exception("Discord Channel ID not found in file.")
        WriteToMainLog("Discord configuration loaded.")
      else:
        raise Exception("Discord settings not found in file.")
    if ConfigFileContents.has_key("Files"):
      WriteToMainLog("Directories loading. . .")
      FileList = ConfigFileContents["Files"]
      if FileList.has_key("AllData"):
        Files["AllData"] = FileList["AllData"]
      else:
        raise Exception("All Data path not found in file.")
      if FileList.has_key("Messages"):
        Files["Messages"] = FileList["Messages"]
      else:
        WriteToMainLog("No messages file found in file. Defaulting to the parent folder of the script.")
      if FileList.has_key("RollAvgPeaks"):
        Files["RollAvgPeaks"] = FileList["RollAvgPeaks"]
      else:
        raise Exception("Rolling Averages Peaks file not found in file.")
      if VariantsEnable:
        if FileList.has_key("Variants"):
          Files["Variants"] = FileList["Variants"]
        else:
          VariantsEnable = False
          WriteToMainLog("Variants file not found in file. Disabling variants function.")
      WriteToMainLog("Directories loaded.")
    else:
      raise Exception("File paths not found in file.")
    if ConfigFileContents.has_key("StatusMessages"):
      StatusMessages = ConfigFileContents["StatusMessages"]
      if StatusMessages.has_key("BlueBannersAddresses"):
        StatusMessagesAddresses["BlueBannersAddresses"] = StatusMessages["BlueBannersAddresses"]
      if StatusMessages.has_key("YellowBannersAddress"):
        StatusMessagesAddresses["YellowBannersAddress"] = StatusMessages["YellowBanners"]
  else:
    Display.lcd_display_string("No config file.")
    raise Exception("The configuration file was not found in the specified directory.\nPlease check the file path and try again.")

def WaitForNetwork():
  global NetworkTestAddresses
  ErrorMode = False
  SuccessfulNetworkCheck = False
  OldLED.on()
  Display.lcd_display_string("Waiting for network.", 4)
  WriteToMainLog("Waiting for network connectivity. . .")
  while not SuccessfulNetworkCheck:
    try:
      for i in range(len(NetworkTestAddresses)):
        WriteToMainLog("Testing connection to IP address " + NetworkTestAddresses[i] + ". . .")
        R = requests.get(NetworkTestAddresses[i])
        if R.status_code != 200 and R.status_code != 204:
          raise Exception("Request fail with status code " + str(R.status_code) + " on address " + NetworkTestAddresses[i])
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

def ReloadLastOutput():
  global CurrentDisplay, DateOfCurrentData, ErrorMode
  if os.path.isfile(Files["AllData"]):
    if os.path.getsize(Files["AllData"]) > 8:
      with open(Files["AllData"], 'r') as AllDataFile:
        NewestRecordFromFile = loads(AllDataFile.read())[0]
      try:
        DateOfCurrentData = NewestRecordFromFile["Date"]
        BuildDisplay(NewestRecordFromFile)
      except:
        PrintError()
        ErrorMode = True
        ErrorLED.on()
        DateOfCurrentData = "1970-01-01"
        CurrentDisplay[1] = "X"
        CurrentDisplay[2] = "Previous data found,".center(20)
        CurrentDisplay[3] = "Data is invalid.".center(20)
    else:
      WriteToMainLog("No previous data found.")
      CurrentDisplay[2] = "No previous".center(20)
      CurrentDisplay[3] = "data found.".center(20)
  else:
    WriteToMainLog("No previous data found.")
    CurrentDisplay[2] = "No previous".center(20)
    CurrentDisplay[3] = "data found.".center(20)
  CommitDisplay(CurrentDisplay)

# Common Procedures
async def TimeReview():
  try:
    global DataAggregationTemplate, ErrorMode, Files, LatestRecordFormatted, PrimaryUpdated, SecondaryUpdated, StatusMessagesAddresses
    await WaitForDiscord()
    await DiscordClient.change_presence(status=discord.Status.idle)
    WriteToMainLog("Beginning time loop.")
    while True:
      CurrentDate = date.today().isoformat()
      CurrentTime = datetime.now().strftime("%H%M")
      Minutes = datetime.now().strftime("%M")
      if DateOfCurrentData == CurrentDate and not PrimaryUpdated:
        PrimaryUpdated = True
        NewLED.on()
        WriteToMainLog("Latest data confirmed.")
      elif not ExcludedDates.__contains__("CurrentDate"):
        if CurrentTime >= BeginTime and not (PrimaryUpdated or SecondaryUpdated):
          WriteToMainLog("Daily data load beginning.")
          LatestRecordFormatted = loads(dumps(DataAggregationTemplate))
          await APICheck()
          WriteToMainLog("Daily data load ending.")
          if PrimaryUpdated:
            await CheckRollAvgPeaks()
          await asyncio.sleep(90)
          await CheckForMessage()
        elif CurrentTime < BeginTime and PrimaryUpdated:
          WriteToMainLog("--- NEW DAY ---", False)
          PrimaryUpdated = False
          SecondaryUpdated = False
          OldLED.off()
          NewLED.off()
          LatestRecordFormatted = loads(dumps(DataAggregationTemplate))
      else:
        if CurrentTime == "0000" and PrimaryUpdated:
          PrimaryUpdated = False
          SecondaryUpdated = False
          OldLED.off()
          NewLED.off()
        if not PrimaryUpdated:
          PrimaryUpdated = True
          WriteToMainLog("No update today.")
          await SendMessage("No data is being released for this day.")
          await CheckForMessage()
          await asyncio.sleep(60)
      if Minutes == "00":
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
  PreviousDate = (date.today() - timedelta(days=1)).isoformat()
  CurrentTime = datetime.today().strftime("%H%M")
  Minutes = datetime.today().strftime("%M")
  OldLED.on()
  MessagesChecked = False
  while not (PrimaryUpdated and SecondaryUpdated) and CurrentTime != TimeoutTime:
    CurrentTime = datetime.today().strftime("%H%M")
    Minutes = datetime.today().strftime("%M")
    if int(Minutes) % 15 == 0:
      if not MessagesChecked:
        await CheckForMessage()
    else:
      MessagesChecked = True
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
          ErrorLED.on()
        PrintError()
    if not SecondaryUpdated:
      try:
        SecondaryUpdated = await SecondaryAPICheck(PreviousDate)
      except:
        PrintError()
    if not (PrimaryUpdated and SecondaryUpdated):
      await asyncio.sleep(DelayTime)
  if CurrentTime == TimeoutTime and not (PrimaryUpdated and SecondaryUpdated):
    ErrorMode = True
    ErrorLED.on()
    await SendMessage(CurrentDate, "Remaining data not sent was not found for this day. Timed out.")
    if not PrimaryUpdated:
      OldLED.off()
      DateOfCurrentData = "1970-01-01"
      NewDisplay = CurrentDisplay[0:4]
      NewDisplay[1] = "NO".center(20)
      NewDisplay[2] = "DATA".center(20)
      NewDisplay[3] = "TODAY".center(20)
      WriteToMainLog("No primary data found. Committing to display.")
      CommitDisplay(NewDisplay)
      CurrentDisplay = NewDisplay[0:4]
    if not SecondaryUpdated:
      WriteToMainLog("No secondary data found.")
  await DiscordClient.change_presence(status=discord.Status.idle)

async def PrimaryAPICheck(Date):
  global DateOfCurrentData, LatestRecordFormatted
  WriteToMainLog("Updating primary. . .")
  LastRecord = APIRequest("PRIMARY")
  WriteToMainLog("Primary updated.")
  Latest = False
  if LastRecord["Date"] == Date:
    WriteToMainLog("Verifying all primary metrics exist. . .")
    if VerifyDataExists("PRIMARY", LastRecord):
      WriteToMainLog("Primary verification passed.")
      if not VerifyMassData(ReloadIfFail=False):
        ReloadMassData(CalculateRollAvgPeak=False)
        LatestRecordFormatted = GetAllData()[0]
      else:
        ParseData(LastRecord)
      BuildDisplay(LatestRecordFormatted)
      OldLED.off()
      NewLED.on()
      AddToAllData()
      await SendData("PRIMARY", LatestRecordFormatted)
      Latest = True
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

# Data Store Refresh & Verification Procedures
def VerifyMassData(ReloadIfFail = True):
  WriteToMainLog("Verifying mass data store integrity. . .")
  AllData = GetAllData()
  DateToCheck = (date.today() - timedelta(days=1))
  for i in range(len(AllData)):
    while ExcludedDates.__contains__(DateToCheck):
      DateToCheck -= timedelta(days=1)
    if AllData[i]["Date"] != DateToCheck:
      if i == 0 and AllData[i]["Date"] != date.today().isoformat():
        WriteToMainLog("Mass data store data not valid.")
        if ReloadIfFail:
          ReloadMassData()
        return False
    else:
      DateToCheck -= timedelta(days=1)
  WriteToMainLog("Mass data store data valid.")
  return True

def ReloadMassData(CalculateRollAvgPeak = True):
  global AllDataAPI, DataAggregationTemplate
  WriteToMainLog("Beginning mass data reload. . .")
  WriteToMainLog("Requesting data from API. . .")
  DataFromAPI = None
  while DataFromAPI == None:
    try:
      DataFromAPI = AllDataAPI.get_json()["data"]
    except:
      PrintError()
  AllData = []
  WriteToMainLog("Data obtained from API. Formatting mass data. . .")
  for i in range(len(DataFromAPI)):
    CurrentRecordFormatting = loads(dumps(DataAggregationTemplate))
    CurrentRecordFormatting["Date"] = DataFromAPI[i]["Date"]
    CurrentRecordFormatting["Day"] = datetime.strptime(DataFromAPI[i]["Date"], "%Y-%m%d").weekday()
    for Metric in Metrics:
      CurrentRecordFormatting[Metric]["New"] = DataFromAPI[i][Metric + "New"]
      CurrentRecordFormatting[Metric]["Total"] = DataFromAPI[i][Metric + "Total"]
    if DataFromAPI[i]["CasesTotal"] != None and DataFromAPI[i]["DeathsTotal"] != None:
      CurrentRecordFormatting["CaseFatality"]["Rate"] = DataFromAPI[i]["DeathsTotal"] / DataFromAPI[i]["CasesTotal"]
    AllData.append(CurrentRecordFormatting)
  WriteToMainLog("Mass data formatted. Calculating rolling averages & daily change. . .")
  AllData = CalculateRollingAveragesAndDailyChange(AllData)
  WriteToMainLog("Rolling averages & daily change calculated.")
  RollAvgPeaks = None
  if CalculateRollAvgPeak:
    WriteToMainLog("Calculating rolling average peaks. . .")
    RollAvgPeaks = CalculateRollAvgPeaks(AllData)
    WriteToMainLog("Rolling average peaks calculated.")
  WriteToMainLog("Committing to file. . .")
  CommitToFile(AllData, RollAvgPeaks)
  WriteToMainLog("Committed to file.")

def CalculateRollingAveragesAndDailyChange(AllData):
  for i in range(len(AllData)):
    for Metric in Metrics:
      if i <= len(AllData) - 7:
        RollingAverageLength = "Seven"
        RollingAverage = AllData[i][Metric]["New"]
        for k in range(1, 7):
          if RollingAverage != None:
            if AllData[i + k][Metric]["New"] != None:
              RollingAverage += AllData[i + k][Metric]["New"]
            else:
              RollingAverage = None
        if RollingAverage != None:
          RollingAverage /= 7
          AllData[i][Metric]["RollingAverage"][RollingAverageLength]["Average"] = RollingAverage
      if i <= len(AllData) - 3:
        RollingAverageLength = "Three"
        RollingAverage = AllData[i][Metric]["New"]
        for k in range(1, 7):
          if RollingAverage != None:
            if AllData[i + k][Metric]["New"] != None:
              RollingAverage += AllData[i + k][Metric]["New"]
            else:
              RollingAverage = None
        if RollingAverage != None:
          RollingAverage /= 3
          AllData[i][Metric]["RollingAverage"][RollingAverageLength]["Average"] = RollingAverage
      if i < len(AllData) - 1:
        if AllData[i][Metric]["New"] != None and AllData[i + 1][Metric]["New"] != None:
          AllData[i][Metric]["Change"] = AllData[i][Metric]["New"] - AllData[i + 1][Metric]["New"]
          AllData[i][Metric]["Corrections"] = AllData[i][Metric]["Total"] - (AllData[i][Metric]["New"] + AllData[i + 1][Metric]["Total"])
        if AllData[i]["CaseFatality"]["Rate"] != None and AllData[i + 1]["CaseFatality"]["Rate"] != None:
          AllData[i]["CaseFatality"]["Change"] = AllData[i]["CaseFatality"]["Rate"] - AllData[i + 1]["CaseFatality"]["Rate"]
        RollingAverages = ["Three", "Seven"]
        for RollingAverage in RollingAverages:
          if AllData[i + 1][Metric]["RollingAverages"][RollingAverage]["Average"] != None:
            AllData[i][Metric]["RollingAverages"][RollingAverage]["Change"] = AllData[i][Metric]["RollingAverages"][RollingAverage]["Average"] - AllData[i + 1][Metric]["RollingAverages"][RollingAverage]["Average"]
  return AllData

def CalculateRollAvgPeaks(AllData):
  RollAvgPeaks = {
    "Cases": {
      "Local": {
        "Date": None,
        "Value": None
      },
      "Global": {
        "Date": None,
        "Value": None
      }
    },
    "Deaths": {
      "Local": {
        "Date": None,
        "Value": None
      },
      "Global": {
        "Date": None,
        "Value": None
      }
    }
  }
  for i in range(len(AllData), -1, -1):
    CasesRA = AllData[i]["Cases"]["RollingAverages"]["Seven"]["Average"]
    DeathsRA = AllData[i]["Deaths"]["RollingAverages"]["Seven"]["Average"]
    CasesRAPeak = False
    DeathsRAPeak = False
    if CasesRA != None:
      if type(RollAvgPeaks["Cases"]["Global"]["Value"]) is float:
        if CasesRA > RollAvgPeaks["Cases"]["Global"]["Value"]:
          RollAvgPeaks["Cases"]["Global"]["Date"] = AllData[i]["Date"]
          RollAvgPeaks["Cases"]["Global"]["Value"] = CasesRA
          RollAvgPeaks["Cases"]["Local"]["Date"] = AllData[i]["Date"]
          RollAvgPeaks["Cases"]["Local"]["Value"] = CasesRA
          CasesRAPeak = True
      else:
        CasesRAPeak = True
        RollAvgPeaks["Cases"]["Global"]["Date"] = AllData[i]["Date"]
        RollAvgPeaks["Cases"]["Global"]["Value"] = CasesRA
        RollAvgPeaks["Cases"]["Local"]["Date"] = AllData[i]["Date"]
        RollAvgPeaks["Cases"]["Local"]["Value"] = CasesRA
      if RollAvgPeaks["Cases"]["Local"]["Value"] == None:
        if AllData[i]["Cases"]["RollingAverages"]["Seven"]["Change"] > 0:
          NumPositives = 1
          while AllData[i + NumPositives]["Cases"]["RollingAverages"]["Seven"]["Change"] > 0:
            NumPositives += 1
          if NumPositives >= 7:
            CasesRAPeak = True
            RollAvgPeaks["Cases"]["Local"]["Date"] = AllData[i]["Date"]
            RollAvgPeaks["Cases"]["Local"]["Value"] = CasesRA
      if not CasesRAPeak and type(RollAvgPeaks["Cases"]["Local"]["Value"]) is float:
        if CasesRA > RollAvgPeaks["Cases"]["Local"]["Value"]:
          CasesRAPeak = True
          RollAvgPeaks["Cases"]["Local"]["Date"] = AllData[i]["Date"]
          RollAvgPeaks["Cases"]["Local"]["Value"] = CasesRA
      if not CasesRAPeak and RollAvgPeaks["Cases"]["Local"]["Date"] != None:
        if AllData[i]["Cases"]["RollingAverages"]["Seven"]["Change"] < 0:
          DateOfLastLocal = datetime.strptime(RollAvgPeaks["Cases"]["Local"]["Date"], "%Y-%m-%d")
          DateOfCurrentData = datetime.strptime(AllData[i]["Date"], "%Y-%m-%d")
          if DateOfCurrentData - DateOfLastLocal >= timedelta(days=10):
            NumNegatives = 1
            while AllData[i + NumNegatives]["Cases"]["RollingAverages"]["Seven"]["Change"] < 0:
              NumNegatives += 1
            if NumNegatives >= 10:
              RollAvgPeaks["Cases"]["Local"]["Date"] = None
              RollAvgPeaks["Cases"]["Local"]["Value"] = None  
    if DeathsRA != None:
      if type(RollAvgPeaks["Deaths"]["Global"]["Value"]) is float:
        if DeathsRA > RollAvgPeaks["Deaths"]["Global"]["Value"]:
          DeathsRAPeak = True
          RollAvgPeaks["Deaths"]["Global"]["Date"] = AllData[i]["Date"]
          RollAvgPeaks["Deaths"]["Global"]["Value"] = DeathsRA
          RollAvgPeaks["Deaths"]["Local"]["Date"] = AllData[i]["Date"]
          RollAvgPeaks["Deaths"]["Local"]["Value"] = DeathsRA
      else:
        DeathsRAPeak = True
        RollAvgPeaks["Deaths"]["Global"]["Date"] = AllData[i]["Date"]
        RollAvgPeaks["Deaths"]["Global"]["Value"] = DeathsRA
        RollAvgPeaks["Deaths"]["Local"]["Date"] = AllData[i]["Date"]
        RollAvgPeaks["Deaths"]["Local"]["Value"] = DeathsRA
      if RollAvgPeaks["Deaths"]["Local"]["Value"] == None:
        if AllData[i]["Deaths"]["RollingAverages"]["Seven"]["Change"] > 0:
          NumPositives = 1
          while AllData[i + NumPositives]["Deaths"]["RollingAverages"]["Seven"]["Change"] > 0:
            NumPositives += 1
          if NumPositives >= 7:
            DeathsRAPeak = True
            RollAvgPeaks["Deaths"]["Local"]["Date"] = AllData[i]["Date"]
            RollAvgPeaks["Deaths"]["Local"]["Value"] = DeathsRA
      if not DeathsRAPeak and type(RollAvgPeaks["Deaths"]["Local"]["Value"]) is float:
        if DeathsRA > RollAvgPeaks["Deaths"]["Local"]["Value"]:
          DeathsRAPeak = True
          RollAvgPeaks["Deaths"]["Local"]["Date"] = AllData[i]["Date"]
          RollAvgPeaks["Deaths"]["Local"]["Value"] = DeathsRA
      if not DeathsRAPeak and RollAvgPeaks["Deaths"]["Local"]["Date"] != None:
        if AllData[i]["Deaths"]["RollingAverages"]["Seven"]["Change"] < 0:
          DateOfLastLocal = datetime.strptime(RollAvgPeaks["Deaths"]["Local"]["Date"], "%Y-%m-%d")
          DateOfCurrentData = datetime.strptime(AllData[i]["Date"], "%Y-%m-%d")
          if DateOfCurrentData - DateOfLastLocal >= timedelta(days=10):
            NumNegatives = 1
            while AllData[i + NumNegatives]["Deaths"]["RollingAverages"]["Seven"]["Change"] < 0:
              NumNegatives += 1
            if NumNegatives >= 10:
              RollAvgPeaks["Deaths"]["Local"]["Date"] = None
              RollAvgPeaks["Deaths"]["Local"]["Value"] = None
  return RollAvgPeaks

def CommitToFile(AllData, RollAvgPeaks):
  with open(Files["AllData"]) as AllDataFile:
    AllDataFile.write("[\n")
    for i in range(len(AllData)):
      AllDataFile.write("  " + dumps(AllData[i]))
      if i != len(AllData) - 1:
        AllDataFile.write(",\n")
    AllDataFile.write("\n]")
  if RollAvgPeaks != None:
    with open(Files["RollAvgPeaks"]) as RollAvgPeaksFile:
      RollAvgPeaksFile.write("[\n")
      RollAvgPeaksFile.write("  \"Cases\": " + dumps(RollAvgPeaks["Cases"] + ",\n"))
      RollAvgPeaksFile.write("  \"Deaths\": " + dumps(RollAvgPeaks["Deaths"]) + "\n")
      RollAvgPeaksFile.write("]")

# Mass Data Handling Procedures
def GetAllData():
  with open(Files["AllData"], 'r') as AllDataFile:
    AllData = loads(AllDataFile.read())
  return AllData

def ParseData(Data):
  global LatestRecordFormatted
  WriteToMainLog("Parsing primary data. . .")
  AllData = GetAllData()
  LatestRecordFormatted["Date"] = Data["Date"]
  LatestRecordFormatted["Day"] = datetime.strptime(Data["Date"], "%Y-%m-%d").weekday()
  for Metric in Metrics:
    LatestRecordFormatted[Metric]["New"] = Data[Metric + "New"]
    LatestRecordFormatted[Metric]["Total"] = Data[Metric + "Total"]
    LatestRecordFormatted["CaseFatality"]["Rate"] = Data["DeathsTotal"] / Data["CasesTotal"]
    if datetime.strptime(AllData[0]["Date"], "%Y-%m-%d") == date.today() - timedelta(days=1):
      if AllData[0]["CaseFatality"]["Rate"] != None:
        LatestRecordFormatted["CaseFatality"]["Change"] = LatestRecordFormatted["CaseFatality"]["Rate"] - AllData[0]["CaseFatality"]["Rate"]
      if AllData[0][Metric]["New"] != None:
        LatestRecordFormatted[Metric]["Change"] = Data[Metric + "New"] - AllData[0][Metric]["New"]
        if AllData[0][Metric]["Total"] != None:
          LatestRecordFormatted[Metric]["Corrections"] = Data[Metric + "Total"] - (Data[Metric + "New"] + AllData[0][Metric]["Total"])
  WriteToMainLog("Parsing complete.")
  CalculateRollingAverages(3, AllData, Data)
  CalculateRollingAverages(7, AllData, Data)

def CalculateRollingAverages(NumOfDays, AllData, NewData):
  global LatestRecordFormatted
  WriteToMainLog("Calculating rolling averages of length " + str(NumOfDays) + ". . .")
  if NumOfDays == 3:
    RollingAverageLength = "Three"
  else:
    RollingAverageLength = "Seven"
  for Metric in Metrics:
    RollingAverage = NewData[Metric + "New"]
    for i in range(NumOfDays - 1):
      if datetime.strptime(AllData[i]["Date"], "%Y-%m-%d") == date.today() - timedelta(days=i + 1): 
        if RollingAverage != None:
          if AllData[i][Metric]["New"] != None:
            RollingAverage += AllData[i][Metric]["New"]
          else:
            RollingAverage = None
      else:
        RollingAverage = None
    if RollingAverage != None:
      RollingAverage /= NumOfDays
      LatestRecordFormatted[Metric]["RollingAverages"][RollingAverageLength]["Average"] = RollingAverage
      if AllData[0][Metric]["RollingAverage"][RollingAverageLength]["Average"] != None:
        LatestRecordFormatted[Metric]["RollingAverages"][RollingAverageLength]["Change"] = RollingAverage - AllData[0][Metric]["RollingAverage"][RollingAverageLength]["Average"]
  WriteToMainLog("Specified rolling average calculated.")

def AddToAllData():
  global LatestRecordFormatted
  ExistingData = GetAllData()
  WriteToMainLog("Adding to mass data. . .")
  if ExistingData[0]["Date"] == LatestRecordFormatted["Date"]:
    WriteToMainLog("Latest data already exists in file.")
  else:
    with open(Files["AllData"], 'w') as AllDataFile:
      AllDataFile.write("[\n")
      Output = "  " + dumps(LatestRecordFormatted)
      AllDataFile.write(Output)
      for Data in ExistingData:
        Output += ",\n  " + dumps(Data)
        AllDataFile.write(Output)
      AllDataFile.write("\n]")
  WriteToMainLog("Data added to mass data store.")

async def CheckRollAvgPeaks():
  Output = []
  if not VerifyMassData(ReloadIfFail=False):
    WriteToMainLog("Main data store not valid. Peaks not calculated.")
    Output.append("An error occurred and the peaks could not be calculated. Please pester the bot admin for an explanation.")
  else:
    WriteToMainLog("Checking rolling average peaks. . .")
    RollAvgPeaks = {
      "Cases": {
        "CreatedLocal": False,
        "NewLocal": False,
        "CreatedGlobal": False,
        "NewGlobal": False,
        "ExpiredLocal": False
      },
      "Deaths": {
        "CreatedLocal": False,
        "NewLocal": False,
        "CreatedGlobal": False,
        "NewGlobal": False,
        "ExpiredLocal": False
      }
    }
    CasesRAPlaceholder = "Cases 7-day rolling average peak"
    DeathsRAPlaceholder = "Deaths 7-day rolling average peak"
    MessagesTemplate = {
      "Cases": {
        "PeakLocal": "New local %CASESPLACEHOLDER% peak.",
        "PeakGlobal": "New global %CASESPLACEHOLDER% peak.",
        "CreatedLocal": "New local %CASESPLACEHOLDER% record created.",
        "CreatedGlobal": "New global %CASESPLACEHOLDER% record created.",
        "ExpiredLocal": "Local %CASESPLACEHOLDER% peak expired."
      },
      "Deaths": {
        "PeakLocal": "New local %DEATHSPLACEHOLDER% peak.",
        "PeakGlobal": "New global %DEATHSPLACEHOLDER% peak.",
        "CreatedLocal": "New local %DEATHSPLACEHOLDER% record created.",
        "CreatedGlobal": "New global %DEATHSPLACEHOLDER% record created.",
        "ExpiredLocal": "Local %DEATHSPLACEHOLDER% peak expired."
      }
    }
    with open(Files["RollAvgPeaks"]) as RollAvgPeaksFile:
      CurrentPeaks = loads(RollAvgPeaksFile.read())
    for Metric in Metrics:
      RollAvgPeaks[Metric] = LookForPeak(Metric.upper(), RollAvgPeaks[Metric], CurrentPeaks)
      if RollAvgPeaks[Metric]["NewGlobal"]:
        if RollAvgPeaks[Metric]["CreatedGlobal"]:
          Output.append(MessagesTemplate[Metric]["CreatedGlobal"])
        Output.append(MessagesTemplate[Metric]["PeakGlobal"])
      if RollAvgPeaks[Metric]["NewLocal"]:
        if RollAvgPeaks[Metric]["CreatedLocal"]:
          Output.append(MessagesTemplate[Metric]["CreatedLocal"])
        Output.append(MessagesTemplate[Metric]["NewLocal"])
      if RollAvgPeaks[Metric]["ExpiredLocal"]:
        Output.append(MessagesTemplate[Metric]["ExpiredLocal"])
    if len(Output) != 0:
      FinalOutput = ""
      for Line in Output:
        FinalOutput += Line.replace("%CASESPLACEHOLDER%", CasesRAPlaceholder).replace("%DEATHSPLACEHOLDER%", DeathsRAPlaceholder) + "\n"
      await SendNotification(FinalOutput)
    else:
      await SendNotification("No peaks today.")
    WriteToMainLog("Rolling average peaks checked.")

def LookForPeak(Metric, Flags, CurrentPeaks):
  Metric = Metric[0] + Metric[1:len(Metric)].lower()
  WriteToMainLog("Checking peaks of metric " + Metric + ". . .")
  if type(CurrentPeaks[Metric]["Global"]["Value"]) is float:
    if LatestRecordFormatted[Metric]["RollingAverages"]["Seven"]["Average"] > CurrentPeaks[Metric]["Global"]["Value"]:
      Flags["NewGlobal"] = True
      CurrentPeaks[Metric]["Global"]["Date"] = LatestRecordFormatted["Date"]
      CurrentPeaks[Metric]["Global"]["Value"] = LatestRecordFormatted[Metric]["RollingAverages"]["Seven"]["Average"]
  else:
    Flags["CreatedGlobal"] = True
    Flags["NewGlobal"] = True
    CurrentPeaks[Metric]["Global"]["Date"] = LatestRecordFormatted["Date"]
    CurrentPeaks[Metric]["Global"]["Value"] = LatestRecordFormatted[Metric]["RollingAverages"]["Seven"]["Average"]
  if CurrentPeaks[Metric]["Local"]["Value"] == None:
    if LatestRecordFormatted[Metric]["RollingAverages"]["Seven"]["Change"] > 0:
      AllData = GetAllData()
      NumPositives = 1
      while AllData[NumPositives][Metric]["RollingAverages"]["Seven"]["Change"] > 0:
        NumPositives += 1
      if NumPositives >= 7:
        Flags["CreatedLocal"] = True
        Flags["NewLocal"] = True
        CurrentPeaks[Metric]["Local"]["Date"] = LatestRecordFormatted["Date"]
        CurrentPeaks[Metric]["Local"]["Value"] = LatestRecordFormatted[Metric]["RollingAverages"]["Seven"]["Average"]
  if not Flags["NewGlobal"] and type(CurrentPeaks[Metric]["Local"]["Value"]) is float:
    if LatestRecordFormatted[Metric]["RollingAverages"]["Seven"]["Average"] > CurrentPeaks[Metric]["Local"]["Value"]:
      Flags["NewLocal"] = True
      CurrentPeaks[Metric]["Local"]["Date"] = LatestRecordFormatted["Date"]
      CurrentPeaks[Metric]["Local"]["Value"] = LatestRecordFormatted[Metric]["RollingAverages"]["Seven"]["Average"]
  if not Flags["NewLocal"] and CurrentPeaks[Metric]["Local"]["Value"] != None:
    if LatestRecordFormatted[Metric]["RollingAverages"]["Seven"]["Change"] < 0:
      DateOfLastLocal = datetime.strptime(CurrentPeaks[Metric]["Local"]["Date"], "%Y-%m-%d")
      CurrentDate = datetime.strptime(LatestRecordFormatted["Date"], "%Y-%m-%d")
      if CurrentDate - DateOfLastLocal >= timedelta(days=10):
        AllData = GetAllData()
        NumNegatives = 1
        while AllData[NumNegatives][Metric]["RollingAverages"]["Seven"]["Change"] < 0:
          NumNegatives += 1
        if NumNegatives >= 10:
          Flags["ExpiredLocal"] = True
          CurrentPeaks[Metric]["Local"]["Date"] = None
          CurrentPeaks[Metric]["Local"]["Value"] = None
  WriteToMainLog("Checking complete for metric " + Metric + ".")
  return Flags

def FindLastHighest(AllData, CheckData, Metric, StartingIndex = 0):
  LastHighestDate = "#N/A; all time highest"
  Metric = Metric[0] + Metric[1:len(Metric)].lower()
  if type(CheckData[Metric]["New"]) is int:
    for i in range(StartingIndex, len(AllData)):
      CurrentIndex = AllData[i]
      if type(CurrentIndex[Metric]["New"]) is int:
        if CurrentIndex[Metric]["New"] > CheckData[Metric]["New"]:
          LastHighestDate = CurrentIndex["Date"] + "; {:,}".format(CurrentIndex[Metric]["New"])
          break
  else:
    LastHighestDate = None
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

def VerifyDate(Date):
  try:
    return datetime.strptime(Date, "%Y-%m-%d")
  except ValueError: 
    return False

def ShowRollAvgPeaks(RequestedMetric = None, RequestedLength = None):
  Output = ""
  if RequestedMetric == None:
    Output += "```\nRolling Average Peaks (7-Day):"
    for Metric in Metrics:
      Output += ShowRollAvgPeaks(Metric.upper())
    Output += "\nThe bot will create a new local peak after 7 consecutive days of positive average change and will expire a local peak after 10 consecutive days of negative average change."
    Output += "\nA new global maximum will not create a local peak if one has not been made using the tests described here."
    Output += "\n```"
  elif RequestedLength == None:
    Lengths = ["Local", "Global"]
    for Length in Lengths:
      Output += ShowRollAvgPeaks(RequestedMetric.upper(), Length.upper())
  else:
    RequestedMetric = RequestedMetric[0] + RequestedMetric[1:len(RequestedMetric)].lower()
    RequestedLength = RequestedLength[0] + RequestedLength[1:len(RequestedLength)].lower()
    with open(Files["RollAvgPeaks"], 'r') as RollAvgPeaksFile:
      RollAvgPeaks = loads(RollAvgPeaksFile.read())
    Output += "\n  " + RequestedMetric + ":"
    Output += "\n    " + RequestedLength + ":"
    if type(RollAvgPeaks[RequestedMetric][RequestedLength]["Value"]) is float:
      Output += "\n      Average: {:,}".format(round(RollAvgPeaks[RequestedMetric][RequestedLength]["Value"], 3))
    else:
      Output += "\n      Average: None"
    Output += "\n      Date:    " + str(RollAvgPeaks[RequestedMetric][RequestedLength]["Date"])
  return Output

# COVID Pi Procedures
def BuildDisplay(Data):
  global CurrentDisplay
  NewDisplay = CurrentDisplay[0:4]
  NewDisplay[1] = "{:,}".format(Data["Cases"]["New"]).rjust(10) + "|" + "{:,}".format(Data["Deaths"]["New"]).rjust(9)
  NewDisplay[2] = "{:,}".format(Data["Cases"]["Total"]).rjust(10) + "|" + "{:,}".format(Data["Deaths"]["Total"]).rjust(9)
  NewDisplay[3] = ""
  if Data["Cases"]["Corrections"] != None:
    NewDisplay[3] += "{:,}".format(Data["Cases"]["Corrections"]).rjust(10)
  else:
    NewDisplay[3] += "None".ljust(10)
  NewDisplay += "|"
  if Data["Deaths"]["Corrections"] != None:
    NewDisplay[3] += "{:,}".format(Data["Deaths"]["Corrections"]).rjust(9)
  else:
    NewDisplay[3] += "None".ljust(9)
  CommitDisplay(NewDisplay)
  CurrentDisplay = NewDisplay[0:4]

def CommitDisplay(NewDisplay):
  WriteToMainLog("Reloading display. . .")
  Display.lcd_clear()
  for i in range(len(NewDisplay)):
    Display.lcd_display_string(NewDisplay[i], i + 1)
  WriteToMainLog("Display reloaded.")

# Discord Procedures
@DiscordClient.event
async def on_ready():
  WriteToMainLog("Discord bot ready as: {0.user}".format(DiscordClient))

async def WaitForDiscord():
  global ErrorMode
  SuccessfulWait = False
  try:
    while not SuccessfulWait:
      WriteToMainLog("Waiting for discord bot to be ready. . .")
      await DiscordClient.wait_until_ready()
      WriteToMainLog("Discord bot ready.")
      SuccessfulWait = True
  except:
    PrintError()
    if not ErrorMode:
      ErrorLED.on()
      ErrorMode = True
    await asyncio.sleep(DelayTime)
  if ErrorMode:
    ErrorMode = False
    ErrorLED.off()

async def SendData(Structure, Data, Index = 0):
  await WaitForDiscord()
  WriteToMainLog("Building Discord message for " + Structure.lower() + " structure. . .")
  Weekdays = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday"
  ]
  Emoji = {
    "Cases": '\U0001F535',
    "Deaths": '\U0001F534',
    "CaseFatality": '\U0001F7E1',
    "Secondary": '\U0001F7E2',
    "Cross": '\u274C'
  }
  ShowLastHighest = VerifyMassData(ReloadIfFail=False)
  if ShowLastHighest:
    AllData = GetAllData()
  NumDecimalPointForRounding = 3
  Output = "```\n"
  if Structure == "PRIMARY":
    RollingAverages = [
      "Three,3",
      "Seven,7"
    ]
    Output += "PRIMARY DATA FOR " + Data["Date"] + ", " + Weekdays[Data["Day"]] + "\n"
    for Metric in Metrics:
      Output += Emoji[Metric] + Metric + ":"
      if type(Data[Metric]["New"]) is int:
        Output += "\n    New:          {:,}".format(Data[Metric]["New"])
      else:
        Output += "\n    New:          None"
      if type(Data[Metric]["Change"]) is int:
        Output += "\n    Change:       {:,}".format(Data[Metric]["Change"]) + GetArrow(Data[Metric]["Change"])
      else:
        Output += "\n    Change:       None" + Emoji["Cases"]
      if ShowLastHighest:
        Output += "\n    Last Highest: " + FindLastHighest(AllData, Data, Metric, Index)
      else:
        Output += "\n    Last Highest: None"
      for RollingAverage in RollingAverages:
        AverageWord = RollingAverage.split(',')[0]
        AverageNumber = RollingAverage.split(',')[1]
        Output += "\n    Roll Avg (" + AverageNumber + "-Day):"
        if type(Data[Metric]["RollingAverages"][AverageWord]["Average"]) is float:
          Output += "\n      Average:    {:,}".format(round(Data[Metric]["RollingAverage"][AverageWord]["Average"], NumDecimalPointForRounding))
        else:
          Output += "\n      Average:    None"
        if type(Data[Metric]["RollingAverages"][AverageWord]["Change"]) is float:
          Output += "\n      Change:     {:,}".format(round(Data[Metric]["RollingAverage"][AverageWord]["Change"], NumDecimalPointForRounding)) + GetArrow(Data[Metric]["RollingAverages"][AverageWord]["Change"])
        else:
          Output += "\n      Change:     None" + Emoji["Cross"]
      if type(Data[Metric]["Corrections"]) is int:
        Output += "\n    Corrections:  {:,}".format(Data[Metric]["Corrections"])
      else:
        Output += "\n    Corrections:  None"
      if type(Data[Metric]["Total"]) is int:
        Output += "\n    Total:        {:,}".format(Data[Metric]["Total"])
      else:
        Output += "\n    Total:        None"
    Output += "\n" + Emoji["CaseFatality"] + "Case-Fatality Rate:"
    if type(Data["CaseFatality"]["Rate"]) is float:
      Output += "\n    Rate:         {:,}%".format(round(Data["CaseFatality"]["Rate"], NumDecimalPointForRounding) * 100)
    else:
      Output += "\n    Rate:         None"
    if type(Data["CaseFatality"]["Change"]) is float:
      Output += "\n    Change:       {:,}p.p.".format(round(Data["CaseFatality"]["Change"], NumDecimalPointForRounding) * 100)
    else:
      Output += "\n    Change:       None"
  elif Structure == "SECONDARY":
    VaccinationDoses = [
      "First",
      "Second",
      "Additional"
    ]
    TotalDoses = {
      "New": 0,
      "Total": 0
    }
    Output += Emoji["Secondary"] + "SECONDARY DATA FOR " + Data["Date"] + ", " + Weekdays[datetime.strptime(Data["Date"], "%Y-%m-%d").weekday()]
    Output += "\n  UK Population: {:,}".format(UKPopulation)
    for Dose in VaccinationDoses:
      if Dose.upper() == "ADDITIONAL":
        Output += "\n  Vaccinations (Additional Doses):"
      else:
        Output += "\n  Vaccinations (" + Dose + " Dose):"
      TotalDoses["New"] += Data["Vaccinations" + Dose + "DoseNew"]
      TotalDoses["Total"] += Data["Vaccinations" + Dose + "DoseTotal"]
      Output += "\n      New:          {:,}".format(Data["Vaccinations" + Dose + "DoseNew"])
      Output += "\n      Total:        {:,}".format(Data["Vaccinations" + Dose + "DoseTotal"])
      Output += "\n      % Population: {:,}%".format(round((Data["Vaccinations" + Dose + "DoseTotal"] / UKPopulation) * 100), NumDecimalPointForRounding)
    Output += "\n  Vaccinations (Total Doses):"
    Output += "\n      New:          {:,}".format(TotalDoses["New"])
    Output += "\n      Total:        {:,}".format(TotalDoses["Total"])
    Output += "\n      % Population: {:,}%".format(round((TotalDoses["Total"] / UKPopulation) * 100), NumDecimalPointForRounding)
  Output += "\n```"
  WriteToMainLog("Sending Discord message for " + Structure.lower() + " structure. . .")
  await SendNotification(Output)
  WriteToMainLog("Discord message sent.")

@DiscordClient.event
async def SendNotification(Notification):
  await WaitForDiscord()
  Channel = DiscordClient.get_channel(id=ChannelID)
  await Channel.send(Notification)

# Discord Commands
@DiscordClient.event
async def on_message(Message):
  try:
    if Message.channel == DiscordClient.get_channel(id=ChannelID) and len(Message.content) > 0:
      if Message.content[0] == "$":
        Command = Message.content.upper()
        if Command.startswith("$GETDATA"):
          WriteToMainLog("Command received of type: \"GETDATA\".")
          GetDataCommand(Command.split(' '))
        elif Command.startswith("$MESSAGES"):
          WriteToMainLog("Command received of type \"MESSAGES\".")
          MessagesCommand()
        elif Command.startswith("$RAVGPEAKS"):
          WriteToMainLog("Command received of type \"RAVGPEAKS\".")
          RollAvgPeaksCommand(Command.split(' '))
        elif Command.startswith("$VARIANT"):
          WriteToMainLog("Command received of type \"VARIANT\".")
          VariantCommand(Command.split(' '))
        elif Command.startswith("$VERSION"):
          WriteToMainLog("Command received of type \"VERSION\".")
          VersionCommand()
        else:
          WriteToMainLog("Command received of unknown type. Returning command help.")
          CommandHelp()
  except:
    PrintError()
    await SendNotification("Unhandled exception occured when parsing your request. Please pester the bot admin for a solution.")

@DiscordClient.event
async def on_message_edit(BeforeMessage, AfterMessage):
  if BeforeMessage.content != AfterMessage.content:
    await on_message(AfterMessage)

async def GetDataCommand(Command):
  if len(Command) == 2:
    if VerifyDate(Command[1]):
      VerifyMassData()  
      WriteToMainLog("Data requested for " + Command[1] + ". Obtaining data. . .")
      AllData = GetAllData()
      DataFound = False
      for i in range(len(AllData)):
        if AllData[i]["Date"] == Command[1]:
          DataFound = True
          WriteToMainLog("Data found.")
          await SendData("PRIMARY", AllData[i], i)
          break
      if not DataFound:
        WriteToMainLog("Data not found.")
        await SendNotification("No data was found for this date.")
    else:
      await SendNotification("`$getdata` command supports date only in ISO 8601 format (YYYY-MM-DD). Omit for the latest data.")
  elif len(Command) == 1:
    VerifyMassData()
    WriteToMainLog("Latest data requested.")
    AllData = GetAllData()
    await SendData("PRIMARY", AllData[0], 0)
  else:
    await SendNotification("`$getdata` command takes zero or one argument of type *date*.")

async def MessagesCommand():
  if not (ResendMessages() or CheckForMessage()):
    await SendNotification("No messages found for today yet.")

async def RollAvgPeaksCommand(Command):
  WriteToMainLog("Obtaining rolling average peaks. . .")
  if len(Command) == 1:
    Output = ShowRollAvgPeaks()
  elif len(Command) == 2:
    if list(map(lambda x:x.upper(), Metrics)).__contains__(Command[1].upper()):
      Output = ShowRollAvgPeaks(Command[1].upper())
    elif Command[2].upper() == "HELP":
      Output = "```\nCommand format: $ravgpeaks [Metric] [Length]"
      Output += "\nMetric and Length parameters are optional. However, the Metric parameter must be included if the Length parameter is to be used.\n"
      Output += "\nValid inputs for Metric:"
      Output += "\n  Cases: return rolling average peaks for cases."
      Output += "\n  Deaths: return rolling average peaks for deaths.\n"
      Output += "\nValid inputs for Length:"
      Output += "\n  Local: returns the current local peak, or none if no peak."
      Output += "\n  Global: returns the current all-time global peak, or none if no peak.\n```"
    else:
      Output = "Invalid command. Please ensure the command meets the format of `$getdata [Metric]`."
  elif len(Command) == 3:
    if list(map(lambda x:x.upper(), Metrics)).__contains__(Command[1].upper()) and ["LOCAL", "GLOBAL"].__contains__(Command[2]):
      Output = ShowRollAvgPeaks(Command[1].upper(), Command[2].upper())
    else:
      Output = "Invalid command. Please ensure the command meets the format of `$getdata [Metric] [Length]`."
  else:
    Output = "Invalid command. Please ensure the command meets the format of `$getdata [Metric] [Length]`."
  await SendNotification(Output)
  WriteToMainLog("Peaks obtained and message sent.")

async def VariantCommand(Command):
  pass

async def VersionCommand():
  Changelog = [

  ]
  Output = "COVID Pi and ~~UK-COV19 Bot~~ Botty-Mc-Bot-Face Version" + Version + ".\nChangelog:\n```"
  for Line in Changelog:
    Output += "\n" + Line
  Output += "\n```"
  await SendNotification(Output)

async def CommandHelp():
  Help = [
    "Command syntax:",
    "  $getdata [date]: Returns the primary data for the date specified.",
    "    date: A date given in ISO 8601 form (YYYY-MM-DD). Omit for the latest data.",
    "  $messages: Outputs any messages for the current day.",
    "  $ravgpeaks: Displays the latest rolling average peaks. Refer to $ravgpeaks help.",
    "  $variant: Returns variant information based on details specified. Refer to $variant help.",
    "  $version: Shows current bot version and changelog from previous version."
  ]
  Output = "```"
  for Line in Help:
    Output += "\n" + Line
  Output += "\n```"
  await SendNotification(Output)

# COVID Variant Procedures
async def VariantLookup(Message):
  pass

def VariantDetails(VariantData, Number):
  pass

# Status Messages
def ReadMessagesFile():
  with open(Files["Messages"], 'r') as MessagesFile:
    ExistingMessages = loads(MessagesFile)
  return ExistingMessages

async def ResendMessages():
  WriteToMainLog("Resending existing messages . . .")
  Messages = ReadMessagesFile()
  CurrentDate = date.today().isoformat()
  MessageSent = False
  for Message in Messages:
    if Message["Date"] == CurrentDate:
      if Message["Type"] == "AdminMessages":
        MessageOrigin = "Bot Admin"
      elif Message["Type"] == "LogBannersMessages" or Message["Type"] == "Announcements":
        MessageOrigin = "Dashboard"
      await SendMessage(CurrentDate, Message["Message"], MessageOrigin)
      MessageSent = True
  if MessageSent:
    WriteToMainLog("Existing messages sent.")
  else:
    WriteToMainLog("No existing messages found.")
  return MessageSent

async def CheckForMessage(CurrentDate = date.today().isoformat()):
  try:
    NewMessages = False
    SuccessfulCheck = False
    ExistingMessages = ReadMessagesFile()
    while not SuccessfulCheck:
      try:
        WriteToMainLog("Checking for administrative messages. . .")
        ExistingMessages = ReadMessagesFile()
        for Message in ExistingMessages:
          if Message["Type"] == "AdminMessages" and Message["Date"] == CurrentDate:
            if not MessageAlreadySent(Message["Body"], ExistingMessages):
              NewMessages = True
              await SendMessage(CurrentDate, Message["Body"], "Bot Admin")
              Message["Sent"] = True
        SuccessfulCheck = True
      except:
        PrintError()
        await asyncio.sleep(DelayTime)
    WriteToMainLog("Administrative messages check completed.")
    SuccessfulCheck = False
    while not SuccessfulCheck:
      try:
        WriteToMainLog("Checking for log banner (blue) messages. . .")
        for Address in StatusMessagesAddresses["BlueBannersAddresses"]:
          Messages = loads(requests.get(Address).text)
          for Message in Messages:
            if Message["date"] == CurrentDate:
              if ["UPDATE", "DATA ISSUE", "CHANGE TO METRIC"].__contains__(Message["type"].upper()):
                if not MessageAlreadySent(Message["body"], ExistingMessages):
                  await SendMessage(CurrentDate, Message["body"], "Dashboard")
                  NewMessages = True
                  ExistingMessages.append(
                    {
                      "Date": CurrentDate,
                      "Message": Message["body"],
                      "Type": "LogBannersMessages",
                      "Sent": True
                    }
                  )
        SuccessfulCheck = True
      except:
        PrintError()
    WriteToMainLog("Log banner messages check completed.")
    SuccessfulCheck = False
    while not SuccessfulCheck:
      try:
        WriteToMainLog("Checking for announcement (yellow) messages. . .")
        Messages = loads(requests.get(StatusMessagesAddresses["YellowBannersAddress"]).text)
        for Message in Messages:
          if Message["date"] == CurrentDate:
            if not MessageAlreadySent(Message["body"], ExistingMessages):
              await SendMessage(CurrentDate, Message["body"], "Dashboard")
              NewMessages = True
              ExistingMessages.append(
                {
                  "Date": CurrentDate,
                    "Message": Message["body"],
                    "Type": "Announcements",
                    "Sent": True
                }
              )
        SuccessfulCheck = True
      except:
        PrintError()
    WriteToMainLog("Announcement messages check completed.")
    if NewMessages:
      WriteToMainLog("Updating messages file. . .")
      with open(Files["Messages"], 'w') as MessagesFile:
        MessagesFile.write("[\n")
        for i in range(len(ExistingMessages)):
          MessagesFile.write("  " + dumps(ExistingMessages[i]))
          if i < len(ExistingMessages) - 1:
            MessagesFile.write(",\n")
        MessagesFile.write("\n]")
      WriteToMainLog("Messages file updated.")
  except:
    PrintError()
    return False
  return NewMessages

def MessageAlreadySent(Message, ExistingMessages, MessageDate):
  for ExistingMessage in ExistingMessages:
    if Message == ExistingMessage["Message"] and ExistingMessage["Date"] == MessageDate:
      return ExistingMessage["Sent"]
  return False

async def SendMessage(Date, Message, MessageOrigin):
  WriteToMainLog("Sending message. . .")
  await WaitForDiscord()
  MessageContents = Message.split("\r\n")
  Output = "Message for " + Date + " from the " + MessageOrigin
  for Paragraph in MessageContents:
    if len(Output + "\n> " + Paragraph) >= 1992:
      Output += "\n(cont)"
      await SendNotification(Output)
      Output += "Continued:"
    Output += "\n> " + Paragraph
  await SendNotification(Output)

# Log Procedures
def WriteToMainLog(Text, Date = True):
  if Date:
    Output = "[" + datetime.now().astimezone().replace(microsecond=0).isoformat(sep='T') + "] " + Text + "\n"
  else:
    Output = Text + "\n"
  with open(Files["RuntimeLogs"], 'a') as LogFile:
    LogFile.write(Output)

def PrintError():
  with open(Files["RuntimeLogs"],'a') as LogFile:
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
    ErrorLogFilename = Files["ErrorLogs"] + "Error_" + datetime.now().strftime("%Y-%m-%dT%H%M%S") + ".txt"
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
    if BeginTime < TimeoutTime:
      raise Exception("Timeout time is later than the start time.")
    POST()
    LoadConfig()
    WaitForNetwork()
    ReloadLastOutput()
    DiscordClient.loop.create_task(TimeReview())
    DiscordClient.run(BotToken)
  except:
    ErrorLED.on()
    OldLED.off()
    NewLED.off()
    Display.lcd_clear()
    Display.lcd_display_string("WARNING!".center(20),1)
    Display.lcd_display_string("The script has quit.",2)
    ErrorLogFilename = Files["ErrorLogs"] + "Error_" + datetime.now().strftime("%Y-%m-%dT%H%M%S") + ".txt"
    with open(ErrorLogFilename,'a') as ErrorFile:
      ErrorFile.write("[" + datetime.now().astimezone().replace(microsecond=0).isoformat(sep='T') + "] Fatal Error (Exception point 2) {\n")
      ErrorFile.write(traceback.format_exc())
      ErrorFile.write("\n}\n")
  while True:
    ErrorLED.off()
    time.sleep(0.9)
    ErrorLED.on()
    time.sleep(0.1)