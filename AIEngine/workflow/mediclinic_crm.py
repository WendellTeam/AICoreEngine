import pandas as pd
import numpy as np
from xlrd import open_workbook
import xlrd
import os
import math
import xlwt
from xlutils.copy import copy
import xlutils
from xlutils.styles import Styles
from dateutil import parser
from directory.movefile import copy_file_to_archived, move_file_to_result_medi
from directory.get_filename_from_path import get_file_name
from utils.Session import session
from utils.audit_trail import *
from utils.logging import logging
from utils.notification import send
from directory.directory_setup import prepare_directories
## INPUT FILES
#bordlisting = r'C:\Users\Asus\Desktop\AETNA\AETNA12521-2020-03.xls'
#disbursementClaim = r'C:\Users\Asus\Desktop\AETNA\MCLXXXX.xls'
def processing_crm(taskid, guid, step_name, bord_file, mcl_file, dcl_file, email=None, num_file=None):
  base = session.base(taskid, guid,email,step_name, filename=bord_file)
  if num_file >=3:
    logging('Processing mos', 'More than 2 files in the processing folder.', base)
  else:
    head, tail = get_file_name(bord_file)
    prepare_directories(head, base)
    populate_data_medi(bord_file, mcl_file, dcl_file, base)
  return 'Success'

def populate_data_medi(bord_file, mcl_file, dcl_file, base):
  disbursementClaim = mcl_file
  bordlisting = bord_file
  disbursementMaster = dcl_file
  audit_log("Processing mediclinic crm process", "Completed...", base)
    
  #Get disbursementMaster path
  #try:
  #    for file in os.listdir(result_path):
  #      if ('running' in file.lower()):
  #        disbursementMaster = result_path + '\\' + file
  #        print(disbursementMaster)

  #except Exception as error:
  #    print('ERROR, path not found')

  #prepare for copy file to achive
  copy_file_to_archived(bord_file)
  copy_file_to_archived(mcl_file)

  try:

      # Get new running no and new row index from disbursementMaster
      print('Open disbursement master file')
      dcm_workbook = open_workbook(disbursementMaster)
      dcm_sheet = dcm_workbook.sheet_by_index(0)
      dcm_df = pd.read_excel(disbursementMaster, sheet_by_index=0, skiprows = 2, usecols = list(range(dcm_sheet.ncols + 1)))

      print('Read running number')
      newRunningNo = dcm_df.iloc[get_DCM_fill_index(disbursementMaster),1]
      newRowIndex = get_DCM_fill_index(disbursementMaster)

      print('Read bord file')
      # Get mapping data from bordereauxListing
      data2 = pd.read_excel(bordlisting)
      data2, skip_row = remove_rows(data2)
      print('skip row: {0}'.format(skip_row))
      wb = xlrd.open_workbook(bordlisting)
      bordlist_df = pd.read_excel(wb)
      #is_insurance = check_insurance_field(bordlist_df)

      try:
        amount_index = data2.columns.get_loc("Clinical Service")-1
      except Exception as error:
        print('Clinical Service column not found. Proceed Clinical Services column name.')
        amount_index = data2.columns.get_loc("Clinical Services")-1

      print('Amount index: {0}'.format(amount_index))
      amount_name = data2.iloc[:,amount_index].name

      print('Read bord case number. {0}'.format(bordlisting))
      totalCases = get_number_cases(bordlisting,skip_row)
      print('Total cases: {0}'.format(totalCases))
      price = data2.loc[get_number_cases(bordlisting,skip_row), amount_name]
      if str(price) == "nan":
        amount_index = data2.columns.get_loc("Clinical Service")-2
        amount_name = data2.iloc[:,amount_index].name
        price = data2.loc[get_number_cases(bordlisting,skip_row), amount_name]
      print('Price: {0}'.format(price))
      initial = data2.loc[get_Initial_index(bordlisting,skip_row, amount_name),amount_name]
      print('Initial: {0}'.format(initial))
      reason = 'O/P MEDICAL CLAIMS'
      #mapping columns data["Unnamed: 0"]
      index = 0
      disbursement_no_index = 0
      client=""

      Is_Aetna = False
      if 'aetna' in bordlisting.lower():
        client = 'AETNA'
        Is_Aetna = True

      for row in bordlist_df["Unnamed: 0"]:
        if str(row) !="nan":
          if "Corporate" in str(row):
            corporate = bordlist_df.iloc[index,2]
            if str(corporate) == "nan":
              corporate = bordlist_df.iloc[index,3]
          elif "Submission Date" in str(row):
            date = bordlist_df.iloc[index,2]
            if str(date) == "nan":
              date = bordlist_df.iloc[index,3]
          elif "Borderaux No" in str(row):
            bord_no = bordlist_df.iloc[index,2]
            if str(bord_no) == "nan":
              bord_no = bordlist_df.iloc[index,3]
          elif "Bordereaux No" in str(row):
            bord_no = bordlist_df.iloc[index,2]
            if str(bord_no) == "nan":
              bord_no = bordlist_df.iloc[index,3]
          elif "Disbursement No" in str(row):
            disbursement_no = bordlist_df.iloc[index, 2]
            disbursement_no_index = index+1
            disbursement_col_index = 2
            if Is_Aetna == True:
              disbursement_semi = " : "
            else:
              disbursement_semi = ""

            if str(disbursement_no) == "nan":
              disbursement_no = bordlist_df.iloc[index,3]
              disbursement_col_index = 3
              disbursement_semi = ""
          elif "Insurance" in str(row):
            client = bordlist_df.iloc[index,2]
            if str(client) == "nan":
              client = bordlist_df.iloc[index,3]
          elif "Insurer" in str(row):
            client = bordlist_df.iloc[index,2]
            if str(client) == "nan":
              client = bordlist_df.iloc[index,3]
        index = index + 1

      print('Date: {0}'.format(date))
      print('Bord no: {0}'.format(bord_no))
      print('Corporate: {0}'.format(corporate))
      print('Reason: {0}'.format(reason))
      print('Client: {0}'.format(client))
      print('Disbursement No: {0}'.format(disbursement_no))

      if disbursement_col_index == 2:
        if Is_Aetna == True:
          if ' : ' in bord_no:
            bord_no = bord_no.replace(' : ', '')
          if ' : ' in corporate:
            corporate = corporate.replace(' : ', '')
          if ' : ' in date:
            date = date.replace(' : ', '')
          try:
            date = parser.parse(date)
          except Except as error:
            print("Date format error: {0}, can be ignore".format(error))

      # Update bordListing
      print('Read bord file.')
      rb = xlrd.open_workbook(bordlisting,formatting_info = True,on_demand=True)
      wb = xlutils.copy.copy(rb) #use copy to get a xlwt workbook
      rb.release_resources()
      w_sheet = wb.get_sheet(0)
      
      # SET STYLE
      alignment = xlwt.Alignment()#设置居中
      alignment.vert = xlwt.Alignment.VERT_CENTER
      font = xlwt.Font()
      font.bold = True
      font.name = 'Arial'
      font.colour_index = xlwt.Style.colour_map['black']
      font.height = 200
      style_BL = xlwt.XFStyle()
      style_BL.alignment = alignment
      style_BL.font = font

      w_sheet.write(disbursement_no_index,disbursement_col_index,disbursement_semi + newRunningNo,style_BL)
      print('Save bord file.')
      wb.save(bordlisting)

      # SET STYLE FOR DISBURSEMENTMASTER
      borders = xlwt.Borders()
      borders.left = 1
      borders.right = 1
      borders.top = 1
      borders.bottom = 1
      alignment = xlwt.Alignment()#设置居中
      alignment.horz = xlwt.Alignment.HORZ_CENTER
      alignment.vert = xlwt.Alignment.VERT_CENTER
      font = xlwt.Font()
      font.name = 'Arial'
      font.colour_index = xlwt.Style.colour_map['red']
      font.height = 160
      
      style_DM = xlwt.XFStyle()
      style_DM.alignment = alignment
      style_DM.font = font
      style_DM.borders = borders

      style_DM1 = xlwt.XFStyle()
      style_DM1.alignment = alignment
      style_DM1.font = font
      style_DM1.borders = borders
      style_DM1.num_format_str = 'dd/MM/yyyy'
  
      style_DM2 = xlwt.XFStyle()
      style_DM2.alignment = alignment
      style_DM2.font = font
      style_DM2.borders = borders
      style_DM2.num_format_str = '#,##0.00'

      ## Update disbursementMaster
      rb = xlrd.open_workbook(disbursementMaster,formatting_info = True,on_demand=True)
      wb = xlutils.copy.copy(rb) #use copy to get a xlwt workbook
      rb.release_resources()
      skiprow = 3
      w_sheet = wb.get_sheet(0)
      w_sheet.write(newRowIndex + skiprow, 0, date,style_DM1)
      w_sheet.write(newRowIndex + skiprow, 3, bord_no,style_DM)
      w_sheet.write(newRowIndex + skiprow, 5, client,style_DM)
      w_sheet.write(newRowIndex + skiprow, 7, price,style_DM2)
      w_sheet.write(newRowIndex + skiprow, 8, reason,style_DM)
      w_sheet.write(newRowIndex + skiprow, 9, initial,style_DM)
      w_sheet.write(newRowIndex + skiprow, 18, totalCases,style_DM)
 
      wb.save(disbursementMaster)


      # Rename disbursementClaim path (MCLXXXXX.xls)

      path, filename = os.path.split(disbursementClaim)
      filename = os.path.splitext(filename)[0]
      filename_split = filename.split(" ")
      newfilename = filename.replace(filename_split[0],newRunningNo)
      newpath = os.path.join(path, newfilename + '.xls')
      os.rename(disbursementClaim,newpath)

      print('Read MCL file')
      mcl = xlrd.open_workbook(newpath)
      mcl_df = pd.read_excel(mcl)
      
      #detect column index
      mcl_index = 1
      for mcl_row in mcl_df.iloc[:, 0]:
        if str(mcl_row) != "nan":
          if "Bill To" in str(mcl_row):
            bill_to_index = mcl_index+1
            print('bill to index: {0}'.format(bill_to_index))
          elif "File no" in str(mcl_row):
            file_no_index = mcl_index
          elif "Company Name" in str(mcl_row):
            comp_name_index = mcl_index
          elif "Total claim incurred" in str(mcl_row):
            total_claim_incurred_index = mcl_index   
        mcl_index = mcl_index + 1

      # Update disbursementClaim
      rb = xlrd.open_workbook(newpath,formatting_info = True,on_demand=True)
      wb = xlutils.copy.copy(rb) #use copy to get a xlwt workbook
      rb.release_resources()
      w_sheet = wb.get_sheet(0)

      #Set Style
      borders1 = xlwt.Borders()
      borders1.left = 1
      borders1.right = 1
      borders1.top = 1
      borders1.bottom = 1
      alignment1 = xlwt.Alignment()#设置居中
      alignment1.horz = xlwt.Alignment.HORZ_CENTER
      alignment1.vert = xlwt.Alignment.VERT_CENTER

      style_DC = xlwt.XFStyle()
      style_DC.alignment = alignment1
      style_DC.borders = borders1
  
      style_DC1 = xlwt.XFStyle()
      style_DC1.alignment = alignment1
      style_DC1.borders = borders1
      style_DC1.num_format_str = 'M/dd/yy'

      alignment2 = xlwt.Alignment()#设置居中
      alignment2.horz = xlwt.Alignment.HORZ_LEFT
      alignment2.vert = xlwt.Alignment.VERT_CENTER
      font2 = xlwt.Font()
      font2.name = 'Arial'
      font2.colour_index = xlwt.Style.colour_map['black']
      font2.height = 160

      style_DC2 = xlwt.XFStyle()
      style_DC2.alignment = alignment2
      style_DC2.font = font2
      style_DC2.num_format_str = '#,##0.00'

      #Set missing cell borders
      borders2 = xlwt.Borders()
      borders2.top = 1
      borders2.right = 1
      borders3 = xlwt.Borders()
      borders3.right = 1
      borders4 = xlwt.Borders()
      borders4.right = 1
      borders4.bottom = 1
      style_DC3 = xlwt.XFStyle()
      style_DC3.borders = borders3
      style_DC4 = xlwt.XFStyle()
      style_DC4.borders = borders2
      style_DC5 = xlwt.XFStyle()
      style_DC5.borders = borders4

      
      font3 = xlwt.Font()
      font3.name = 'Tahoma'
      font3.bold = True
      font3.colour_index = xlwt.Style.colour_map['black']
      font3.height = 200
      alignment3 = xlwt.Alignment()#设置居中
      alignment3.horz = xlwt.Alignment.HORZ_CENTER
      alignment3.vert = xlwt.Alignment.VERT_CENTER
      style_DC6 = xlwt.XFStyle()
      style_DC6.font = font3
      style_DC6.alignment = alignment3
      style_DC6.borders = borders3
      style_DC6.num_format_str = '#,##0.00'
      style_DC7 = xlwt.XFStyle()
      style_DC7.font = font3
      style_DC7.alignment = alignment3
      style_DC7.borders = borders4
      style_DC7.num_format_str = '#,##0.00'

      total_address_row = (file_no_index-1) - (bill_to_index) -1
      print('Total address row: {0}'.format(total_address_row))
      
      w_sheet.write(file_no_index+1, 3, newRunningNo,style_DC)
      w_sheet.write(file_no_index+1, 8, date,style_DC1)
      w_sheet.write(comp_name_index+1, 7, price,style_DC2)
      w_sheet.write(bill_to_index, 5, '',style_DC4)
      for i in range(total_address_row):
        w_sheet.write((bill_to_index+1)+i, 5, '',style_DC3)
      w_sheet.write(file_no_index-2, 5, '',style_DC5)
      w_sheet.write(total_claim_incurred_index, 8, 'RM ' + '{:,.2f}'.format(price),style_DC6)
      w_sheet.write(total_claim_incurred_index+3, 8, 'RM ' + '{:,.2f}'.format(price),style_DC7)
      
      wb.save(newpath)

      destination_result = move_file_to_result_medi(newpath)
      destination_brdx = move_file_to_result_medi(bordlisting)
      head, tail = get_file_name(destination_result)
      
      audit_log("Move file to result.", "Completed...", base)

      #send notification
      if base.email != None:
        send(base, base.email, "RPA Task Execution Completed.",
                           "Hi, <br/><br/><br/>You task has been completed. "+
                           "<br/>Reference Number: " + str(base.guid) + "<br/>"+
                           "Result file as following link: <"+head+"><br/>"+
                           "<br/>Regards,<br/>Robotic Process Automation")

      audit_log("End process for MediClinic CRM", "Completed...", base)
  except Exception as error:
      logging('populate_data_medi', error, base)
      print('ERROR: {0}'.format(error))

def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text  # or whatever

def check_insurance_field(data):
  if data["Unnamed: 0"][0] == "Corporate :":
    return False
  else:
    return True

def remove_rows(data):
  for index, item in data.iterrows():
    #print('Index: {0}, item value: {1}'.format(index, item[0]))
    if str(item[0]).lower()=='no':
      new_header = data.iloc[index]
      #print('New header: {0}'.format(new_header))
      data = data[index+1:]
      data.columns = new_header
      data.reset_index(drop=True, inplace=True)
      return data, index+1
  return data, 0

### FROM medi_update_dcm
def get_DCM_fill_index(disbursementMaster):
  data = pd.read_excel(disbursementMaster,skiprows = 2 , na_values = "Missing")
  Bord_No_list = pd.DataFrame(data, columns=['Bord No']).values.tolist()
  counter = len(Bord_No_list) - 1
  try:
    while True:
      math.isnan(Bord_No_list[counter][0])
      counter-=1
  except:
    a = None
  fill_index = counter + 1
  return fill_index

def get_number_cases(bordereauxListing,skip_row):
  data = pd.read_excel(bordereauxListing,skiprows = skip_row , na_values = "Missing")
  
  claim_id_list = pd.DataFrame(data, columns=['Claim Id']).values.tolist()
  counter = len(claim_id_list) - 1
  try:
    while True:
      math.isnan(claim_id_list[counter][0])
      counter-=1
  except:
    a = None
  fill_index = counter + 1
  return fill_index
  

def get_Initial_index(bordereauxListing, skip_row, amount_index):
  data = pd.read_excel(bordereauxListing,skiprows = skip_row , na_values = "Missing")
  data.columns
  Aetna_Amount_Column_list = pd.DataFrame(data, columns=[amount_index]).values.tolist()
  counter = len(Aetna_Amount_Column_list) - 1
  try:
    while True:
      math.isnan(Aetna_Amount_Column_list[counter][0])
      counter-=1
  except:
    a = None
  fill_index = counter - 1
  return fill_index
