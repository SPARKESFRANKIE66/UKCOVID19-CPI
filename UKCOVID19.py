from datetime import date, datetime, timedelta
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
ExcludedDates = [

]
LatestRecordFormatted = loads(dumps(DataAggregationTemplate))
PrimaryUpdated = False
SecondaryUpdated = False
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
      if Configuration.has_key("VariantsEnable"):
        VariantsEnable = Configuration["VariantsEnable"]
      else:
        WriteToMainLog("Variants toggle not found in file. Using default value.")
      if Configuration.has_key("WaitTime"):
          DelayTime = Configuration["WaitTime"]
      else:
        WriteToMainLog("Wait time not found in configuration file. Using default wait time.")
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
  global CurrentDisplay, DateOfCurrentData, ErrorMode, LatestRecordFormatted
  if os.path.isfile(Files["AllData"]):
    if os.path.getsize(Files["AllData"]) > 8:
      with open(Files["AllData"], 'r') as AllDataFile:
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
      if Minutes == "00":
        await CheckForMessage()
        await asyncio.sleep(55)
      await asyncio.sleep(5)
  except:
    await FatalException()

async def APICheck():
  pass

async def PrimaryAPICheck():
  pass

async def SecondaryAPICheck():
  pass

def APIRequest(Structure):
  pass

def VerifyDataExists(Structure, Data):
  pass

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

def ReloadMassData():
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
    CurrentRecordFormatting["Cases"]["New"] = DataFromAPI[i]["CasesNew"]
    CurrentRecordFormatting["Cases"]["Total"] = DataFromAPI[i]["CasesTotal"]
    CurrentRecordFormatting["Deaths"]["New"] = DataFromAPI[i]["DeathsNew"]
    CurrentRecordFormatting["Deaths"]["Total"] = DataFromAPI[i]["DeathsTotal"]
    if DataFromAPI[i]["CasesTotal"] != None and DataFromAPI[i]["DeathsTotal"] != None:
      CurrentRecordFormatting["CaseFatality"]["Rate"] = DataFromAPI[i]["DeathsTotal"] / DataFromAPI[i]["CasesTotal"]
    AllData.append(CurrentRecordFormatting)
  WriteToMainLog("Mass data formatted. Calculating rolling averages & daily change. . .")
  AllData = CalculateRollingAveragesAndDailyChange(AllData)
  WriteToMainLog("Rolling averages & daily change calculated. Calculating rolling average peaks. . .")
  RollAvgPeaks = CalculateRollAvgPeaks(AllData)
  WriteToMainLog("Rolling average peaks calculated. Committing to file. . .")
  CommitToFile(AllData, RollAvgPeaks)
  WriteToMainLog("Committed to file.")

def CalculateRollingAveragesAndDailyChange(AllData):
  for i in range(len(AllData)):
    if i <= len(AllData) - 7:
      RollingAverageLength = "Seven"
      CasesRollingAverage = AllData[i]["Cases"]["New"]
      DeathsRollingAverage = AllData[i]["Deaths"]["New"]
      for k in range(1, 7):
        if CasesRollingAverage != None:
          if AllData[i + k]["Cases"]["New"] != None:
            CasesRollingAverage += AllData[i + k]["Cases"]["New"]
          else:
            CasesRollingAverage = None
        if DeathsRollingAverage != None:
          if AllData[i + k]["Deaths"]["New"] != None:
            DeathsRollingAverage += AllData[i + k]["Deaths"]["New"]
          else:
            DeathsRollingAverage = None
      if CasesRollingAverage != None:
        CasesRollingAverage /= 7
        AllData[i]["Cases"]["RollingAverage"][RollingAverageLength]["Average"] = CasesRollingAverage
      if DeathsRollingAverage != None:
        DeathsRollingAverage /= 7
        AllData[i]["Deaths"]["RollingAverage"][RollingAverageLength]["Average"] = DeathsRollingAverage
    if i <= len(AllData) - 3:
      RollingAverageLength = "Three"
      CasesRollingAverage = AllData[i]["Cases"]["New"]
      DeathsRollingAverage = AllData[i]["Deaths"]["New"]
      for k in range(1, 7):
        if CasesRollingAverage != None:
          if AllData[i + k]["Cases"]["New"] != None:
            CasesRollingAverage += AllData[i + k]["Cases"]["New"]
          else:
            CasesRollingAverage = None
        if DeathsRollingAverage != None:
          if AllData[i + k]["Deaths"]["New"] != None:
            DeathsRollingAverage += AllData[i + k]["Deaths"]["New"]
          else:
            DeathsRollingAverage = None
      if CasesRollingAverage != None:
        CasesRollingAverage /= 3
        AllData[i]["Cases"]["RollingAverage"][RollingAverageLength]["Average"] = CasesRollingAverage
      if DeathsRollingAverage != None:
        DeathsRollingAverage /= 3
        AllData[i]["Deaths"]["RollingAverage"][RollingAverageLength]["Average"] = DeathsRollingAverage
    if i < len(AllData) - 1:
      if AllData[i]["Cases"]["New"] != None and AllData[i + 1]["Cases"]["New"] != None:
        AllData[i]["Cases"]["Change"] = AllData[i]["Cases"]["New"] - AllData[i + 1]["Cases"]["New"]
        AllData[i]["Cases"]["Corrections"] = AllData[i]["Cases"]["Total"] - (AllData[i]["Cases"]["New"] + AllData[i + 1]["Cases"]["Total"])
      if AllData[i]["Deaths"]["New"] != None and AllData[i + 1]["Deaths"]["New"] != None:
        AllData[i]["Deaths"]["Change"] = AllData[i]["Deaths"]["New"] - AllData[i + 1]["Deaths"]["New"]
        AllData[i]["Deaths"]["Corrections"] = AllData[i]["Deaths"]["Total"] - (AllData[i]["Deaths"]["New"] + AllData[i + 1]["Deaths"]["Total"])
      if AllData[i]["CaseFatality"]["Rate"] != None and AllData[i + 1]["CaseFatality"]["Rate"] != None:
        AllData[i]["CaseFatality"]["Change"] = AllData[i]["CaseFatality"]["Rate"] - AllData[i + 1]["CaseFatality"]["Rate"]
      if AllData[i + 1]["Cases"]["RollingAverages"]["Three"]["Average"] != None:
        AllData[i]["Cases"]["RollingAverages"]["Three"]["Change"] = AllData[i]["Cases"]["RollingAverages"]["Three"]["Average"] - AllData[i + 1]["Cases"]["RollingAverages"]["Three"]["Average"]
      if AllData[i + 1]["Cases"]["RollingAverages"]["Seven"]["Average"] != None:
        AllData[i]["Cases"]["RollingAverages"]["Seven"]["Change"] = AllData[i]["Cases"]["RollingAverages"]["Seven"]["Average"] - AllData[i + 1]["Cases"]["RollingAverages"]["Seven"]["Average"]
      if AllData[i + 1]["Deaths"]["RollingAverages"]["Three"]["Average"] != None:
        AllData[i]["Deaths"]["RollingAverages"]["Three"]["Change"] = AllData[i]["Deaths"]["RollingAverages"]["Three"]["Average"] - AllData[i + 1]["Deaths"]["RollingAverages"]["Three"]["Average"]
      if AllData[i + 1]["Deaths"]["RollingAverages"]["Seven"]["Average"] != None:
        AllData[i]["Deaths"]["RollingAverages"]["Seven"]["Change"] = AllData[i]["Deaths"]["RollingAverages"]["Seven"]["Average"] - AllData[i + 1]["Deaths"]["RollingAverages"]["Seven"]["Average"]
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
              ChangesMade = True
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
  with open(Files["RollAvgPeaks"]) as RollAvgPeaksFile:
    RollAvgPeaksFile.write("[\n")
    RollAvgPeaksFile.write("  \"Cases\": " + dumps(RollAvgPeaks["Cases"] + ",\n"))
    RollAvgPeaksFile.write("  \"Deaths\": " + dumps(RollAvgPeaks["Deaths"]) + "\n")
    RollAvgPeaksFile.write("]")

# Mass Data Handling Procedures
def GetAllData():
  pass

def ParseData(Data):
  pass

def CalculateRollingAverages(NumOfDays, AllData, NewData):
  pass

def AddToAllData():
  pass

async def CheckRollAvgPeaks():
  pass

def FindLastHighest(AllData, CheckData, Metric, StartingIndex = 0):
  pass

def GetArrow(Value):
  pass

def VerifyDate(Date):
  pass

# COVID Pi Procedures
def CommitDisplay(NewDisplay):
  pass

def WriteLastDisplay():
  pass

# Discord Procedures
@DiscordClient.event
async def on_ready():
  pass

@DiscordClient.event
async def on_message(Message):
  pass

@DiscordClient.event
async def on_message_edit(BeforeMessage, AfterMessage):
  pass

async def WaitForDiscord():
  pass

@DiscordClient.event
async def SendData(Structure, Data, Index = 0):
  pass

@DiscordClient.event
async def SendNotification(Notification):
  pass

# COVID Variant Procedures
async def VariantLookup(Message):
  pass

def VariantDetails(VariantData, Number):
  pass

# Status Messages
async def CheckForMessage(CurrentDate = None, IgnoreSent = False):
  pass

def MessageAlreadySent(Message, MessageFileContents, IgnoreSent):
  pass

@DiscordClient.event
async def SendMessage(Date, Message, MessageType):
  pass

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