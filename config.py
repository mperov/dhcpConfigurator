#!/usr/bin/env python

# Author: Maxim Perov (mperov@okbsapr.ru)

import gtk, sys, os, gobject

from pyparsing import *

COUNT_COLUMN_GENERAL = 6
COUNT_COLUMN_HOSTS = 6
COUNT_COLUMN_SUBNETS = 5

GENERAL_TYPE_TABLE = 0
HOSTS_TYPE_TABLE = 1
SUBNETS_TYPE_TABLE = 2

OPTION_TEXT_COMBOBOX = "your additions"

NUMBER_HOSTS_RANGE = 4
NUMBER_SUBNETS_RANGE = 3

class Parser:
  digits = "0123456789"
  colon,semi,period,comma,lbrace,rbrace,quote = map(Literal,':;.,{}"')
  number = Word(digits)
  hexint = Word(hexnums,exact = 2)
  dnschars = Word(alphanums + '-') # characters permissible in DNS names

  mac = Combine(hexint + (":" + hexint) * 5)
  ip = Combine(number + period + number + period + number + period + number)
  ips = delimitedList(ip)
  hostname = dnschars
  domainname = dnschars + ZeroOrMore("." + dnschars)
  domain_names = delimitedList(Combine(domainname))

  fqdn = Combine(hostname + ZeroOrMore(period + domainname))
  fixed_address  = StringStart() + Literal('fixed-address') + ips
  ddns_hostname = StringStart() + Literal('ddns-hostname') + hostname
  ddns_domainname = StringStart() + Literal('ddns-domainname') + Combine(quote + domainname + quote)
  note = ZeroOrMore(Combine(Literal('#') + restOfLine))
  hardware_ethernet = StringStart() + Literal('hardware ethernet') + mac
  anything = ZeroOrMore(Word(alphanums + "!@#$%^&*)(_+:\"\'=-?.,>< ") + semi)
  range_ips = StringStart() + Literal('range') + ip * 2

  d_hosts = { }
  d_subnets = { }
  d_global_parameters = { }

  def get_string_of_pattern_for_host(self, l_some, pattern):
    for s_word in l_some:
      grammar_word = pattern
      parse_word_results = grammar_word.searchString(s_word)
      for group in parse_word_results:
        self.d_hosts[l_some[1]][group[0]] = group[1]


  def get_hosts_from_text(self, s_text_dhcp):
    # Put the grammar together to define a host declaration
    parse_host =  Literal('host') + self.fqdn + self.lbrace + (self.note & self.anything) + self.rbrace

    parse_results = parse_host.scanString(s_text_dhcp)

    for result in parse_results:
      l_result = list(result[0])
      self.d_hosts[l_result[1]] = { }

      # get string with range ip address 
      l_tmp = [ ]

      for s_word in l_result:
        grammar_word = self.range_ips
        parse_word_results = grammar_word.searchString(s_word)
        for s_ip in parse_word_results:
          l_tmp.append(s_ip[1])
          l_tmp.append(s_ip[2])
          self.d_hosts[l_result[1]][parse_word_results[0][0]] = l_tmp

      # get string with fixed address 
      l_tmp = [ ]

      for s_word in l_result:
        grammar_word = self.fixed_address
        parse_word_results = grammar_word.searchString(s_word)
        for group_fixed_ip in parse_word_results:
          for s_ip in group_fixed_ip:
            if s_ip != 'fixed-address':
              l_tmp.append(s_ip)
          self.d_hosts[l_result[1]][group_fixed_ip[0]] = l_tmp

      # get string with mac address
      self.get_string_of_pattern_for_host(l_result, self.hardware_ethernet)
      # get string with DDNS host name
      self.get_string_of_pattern_for_host(l_result, self.ddns_hostname)
      # get string with DDNS domain name
      self.get_string_of_pattern_for_host(l_result, self.ddns_domainname)

      # here you can add your code


  def get_string_of_pattern_for_subnets(self, l_some, s_pattern):
    for s_word in l_some:
      grammar_word = StringStart() + Literal(s_pattern) + self.number
      parse_word_results = grammar_word.searchString(s_word)
      for group_dft in parse_word_results:
        self.d_subnets[l_some[1] + ':' + l_some[3]][group_dft[0]] = group_dft[1]


  def get_subnets_from_text(self, s_text_dhcp):
    # Put the grammar together to define a subnet declaration
    parse_subnet = Literal('subnet') + self.ip + Literal('netmask') + self.ip + self.lbrace + (self.note & self.anything) + self.rbrace

    parse_results = parse_subnet.scanString(s_text_dhcp)

    for result in parse_results:
      l_result = list(result[0])
      self.d_subnets[l_result[1] + ':' + l_result[3]] = { }
      # get string with range ip
      l_tmp = [ ]

      for s_word in l_result:
        grammar_word = self.range_ips
        parse_word_results = grammar_word.searchString(s_word)
        for s_ip in parse_word_results:
          l_tmp.append(s_ip[1])
          l_tmp.append(s_ip[2])
          self.d_subnets[l_result[1] + ':' + l_result[3]][parse_word_results[0][0]] = l_tmp

      # get string with default-lease-time
      self.get_string_of_pattern_for_subnets(l_result, 'default-lease-time')
      # get string with max-lease-time 
      self.get_string_of_pattern_for_subnets(l_result, 'max-lease-time')

      # here you can add your code

  def get_string_of_pattern_for_global(self, s_some, s_pattern, pp_pattern): # pp = pyparsing
    parse_global_parameter = StringStart() + Literal(s_pattern) + pp_pattern
    parse_line_results = parse_global_parameter.searchString(s_some)
    if len(parse_line_results) > 0:
      self.d_global_parameters[parse_line_results[0][0]] = parse_line_results[0][1]


  def get_global_parameters_from_text(self, s_text_dhcp):
    i_count_lbrace = 0
    i_count_rbrace = 0

    l_lines = s_text_dhcp.split('\n')
    for s_line in l_lines:
      # count {
      i_place_l = s_line.find('{')
      if i_place_l >= 0:
        i_place_sharp = s_line.find('#')
        if i_place_sharp == -1:
          i_count_lbrace = i_count_lbrace + 1
        else:
          if i_place_sharp > i_place_l:
            i_count_lbrace = i_count_lbrace +1
      # count }
      i_place_r = s_line.find('}')
      if i_place_r >= 0:
        i_place_sharp = s_line.find('#')
        if i_place_sharp == -1:
          i_count_rbrace = i_count_rbrace + 1
        else:
          if i_place_sharp > i_place_r:
            i_count_rbrace = i_count_rbrace +1
      if i_count_lbrace == i_count_rbrace:
        # find global parameter (default_lease-time)
        self.get_string_of_pattern_for_global(s_line, 'default-lease-time', self.number)

        # find (option domain-name)
        self.get_string_of_pattern_for_global(s_line, 'option domain-name', Word(alphanums + "\".@"))

        # find (max-lease-time)
        self.get_string_of_pattern_for_global(s_line, 'max-lease-time', self.number)

        # find (option domain-name-servers)
        parse_global_parameter = StringStart() + Literal('option domain-name-servers') + self.domain_names
        parse_line_results = parse_global_parameter.searchString(s_line)
        l_tmp = [ ]
        for group_domain_name in parse_line_results:
          for s_name in group_domain_name:
            if s_name != 'option domain-name-servers':
              l_tmp.append(s_name)
          self.d_global_parameters[group_domain_name[0]] = l_tmp
        # find (ddns-update-style)
	self.get_string_of_pattern_for_global(s_line, 'ddns-update-style', Word(alphanums))

        # find (log-facility)
        self.get_string_of_pattern_for_global(s_line, 'log-facility', Word(alphanums))


  def get_text_from_file(self, s_file_name):
    f_dhcp = open(s_file_name, 'rU')
    return f_dhcp.read()


######################################################## MAIN CLASS
class Main:

  builder = None
  s_text_dhcp = ''
  iter_first_combo = None
  iter_combo_fa = None
  our_parser = None
  iter_combo_range = None
  iter_combo_srange = None


  def exit(self, widget):
    sys.exit(0)


  def print_to_file(self, s_file_name, d_global_parameters, d_subnets, d_hosts):
    f_out = open(s_file_name,"w")

    # print global parameters
    f_out.write('\n\n')
    for key in d_global_parameters:
      f_out.write(key + ' ')
      if key == 'option domain-name-servers':
        for i in range(len(d_global_parameters[key])):
          f_out.write(' ' + d_global_parameters[key][i])
          if i < len(d_global_parameters[key])-1:
            f_out.write(',')
          else:
            f_out.write(';')
      else:
        f_out.write(' ' + d_global_parameters[key] + ';')
      f_out.write('\n')
    f_out.write('\n\n')

    # print d_subnets
    for key in d_subnets:
      d_ip_mask = key.split(':')
      f_out.write('subnet ' + d_ip_mask[0] + ' netmask ' + d_ip_mask[1] + ' {\n')
      for sub_key in d_subnets[key]:
        f_out.write('\t' + sub_key)
        if sub_key == 'range':
          count_for_range = 0
          for i in range(len(d_subnets[key][sub_key])):
            count_for_range = count_for_range + 1
            f_out.write(' ' + d_subnets[key][sub_key][i])
            if count_for_range > 1 and sub_key == 'range' and i < len(d_subnets[key][sub_key])-1:
              f_out.write(';\n')
              f_out.write('\trange')
              count_for_range = 0
            if i < len(d_subnets[key][sub_key])-1:
              f_out.write('')
            else:
              f_out.write(';')
        else:
          f_out.write(' ' + d_subnets[key][sub_key] + ';')
        f_out.write('\n')
      f_out.write('}\n\n')


    # print d_hosts 
    for key in d_hosts:
      f_out.write('host ' + key + ' {\n')
      for sub_key in d_hosts[key]:
        f_out.write('\t' + sub_key)
        if sub_key == 'fixed-address':
          count_for_range = 0
          for ip_addr in d_hosts[key][sub_key]:
            count_for_range = count_for_range + 1
            if count_for_range > 1:
              f_out.write(',  ' + ip_addr)
            else:
              f_out.write('  ' + ip_addr)
          f_out.write(';')
        elif sub_key == 'range':
          count_for_range = 0
          for i in range(len(d_hosts[key][sub_key])):
            count_for_range = count_for_range + 1
            f_out.write(' ' + d_hosts[key][sub_key][i])
            if count_for_range > 1 and sub_key == 'range' and i < len(d_hosts[key][sub_key])-1:
              f_out.write(';\n')
              f_out.write('\trange')
              count_for_range = 0
            if i < len(d_hosts[key][sub_key])-1:
              if sub_key != 'range':
                f_out.write(',')
              else:
                f_out.write('')
            else:
              f_out.write(';')
        else:
          f_out.write(' ' + d_hosts[key][sub_key] + ';')
        f_out.write('\n')
      f_out.write('}\n\n')
    f_out.close()


  # get global dict from cells
  def get_global_dict_from_cells(self):
    d_global_param = { }
    for i in range(COUNT_COLUMN_GENERAL):
      string = 'generaltreeviewcolumn' + str(i+1)
      general_liststore = self.builder.get_object("for_general")
      s_column_title = self.builder.get_object(string).get_title()
      s_tmp = general_liststore[0][i]
      if s_tmp.strip() != '':
        if s_column_title == 'option domain-name-servers':
          l_tmp = [ ]
          # getting strings from combobox
          combo_model = self.builder.get_object("for_combo")
          # for it using iterator
          iter_tmp = combo_model.get_iter_first()
          for k in range(len(combo_model)):
            s_tmp_value = combo_model.get_value(iter_tmp, 0)
            if s_tmp_value != OPTION_TEXT_COMBOBOX:
              l_tmp.append(s_tmp_value)
            iter_tmp = combo_model.iter_next(iter_tmp)
          # set in the dict our the  got list with strings
          d_global_param[s_column_title] = l_tmp
        else:
          d_global_param[ s_column_title ] = s_tmp
    return d_global_param


  # get global dict from cells		
  def get_hosts_dict_from_cells(self):
    d_hosts_param = { }
    hosts_liststore = self.builder.get_object("for_hosts")
    i = 0
    host = self.builder.get_object('hoststreeviewcolumn1').get_title()
    while ( hosts_liststore[i][0].strip() != ''):
      d_hosts_param[ hosts_liststore[i][0] ] = { }
      for j in range(COUNT_COLUMN_HOSTS - 1):
        string = 'hoststreeviewcolumn' + str(j + 2)
        s_column_title = self.builder.get_object(string).get_title()

        if hosts_liststore[i][j+1].strip() != '' and hosts_liststore[i][j+1].strip() != OPTION_TEXT_COMBOBOX:
          if s_column_title == 'fixed-address' or s_column_title == 'range':
            d_hosts_param[ hosts_liststore[i][0] ][s_column_title] = self.our_parser.d_hosts[ hosts_liststore[i][0] ][s_column_title]
          else:
            d_hosts_param[ hosts_liststore[i][0] ][s_column_title] = hosts_liststore[i][j+1]
      i = i + 1
    return d_hosts_param


  # get global dict from cells
  def get_subnets_dict_from_cells(self):
    d_subnets_param = { }
    subnets_liststore = self.builder.get_object("for_subnets")
    i = 0
    sub = self.builder.get_object('subnetstreeviewcolumn1').get_title()
    while ( subnets_liststore[i][0].strip() != ''):
      d_subnets_param[ subnets_liststore[i][0] + ':' + subnets_liststore[i][1] ] = { }
      for j in range(COUNT_COLUMN_SUBNETS - 2):
        string = 'subnetstreeviewcolumn' + str(j+3)
        s_column_title = self.builder.get_object(string).get_title()
        if subnets_liststore[i][j + 2].strip() != '':
          if s_column_title == 'range':
            d_subnets_param[ subnets_liststore[i][0] + ':' + subnets_liststore[i][1] ][s_column_title] = self.our_parser.d_subnets[ subnets_liststore[i][0] + ':' + subnets_liststore[i][1] ][s_column_title]
          else:
            d_subnets_param[ subnets_liststore[i][0] + ':' + subnets_liststore[i][1] ][s_column_title] = subnets_liststore[i][j + 2]
      i = i + 1
    return d_subnets_param

  # this func saves special parameters in dicts of Parser
  # e.g. range, fixed-address, etc
  def memorize_data_in_common_dict(self, row, column, model, combo_model, type_table):
    if type_table == HOSTS_TYPE_TABLE:
      s_host = model[row][0]
      s_column_title = self.builder.get_object("hoststreeviewcolumn" + str(column + 1)).get_title()
      l_tmp = [ ]
      iter_tmp = combo_model.get_iter_first()
      while True:
        s_tmp = str(combo_model.get_value(iter_tmp, 0))
        if s_tmp == OPTION_TEXT_COMBOBOX:
          break
        # chosing range's column  
        if column == 3:
          l_tmp.append(s_tmp.split('-')[0].strip())
          l_tmp.append(s_tmp.split('-')[1].strip())
        else: # other column
          l_tmp.append(s_tmp)
        iter_tmp = combo_model.iter_next(iter_tmp)

################ FIRST STEP FOR MAKING TEST OF INPUT DATA ##############
      if s_host == '':
        return
      # detecting existing dict of s_host
      try:
        self.our_parser.d_hosts[s_host] == None
      except:
        self.our_parser.d_hosts[s_host] = { }
      print l_tmp
      self.our_parser.d_hosts[s_host][s_column_title] = l_tmp

    if type_table == SUBNETS_TYPE_TABLE:
      s_sub = model[row][0] + ':' + model[row][1]
      s_column_title = self.builder.get_object("subnetstreeviewcolumn" + str(column + 1)).get_title()
      l_tmp = [ ]

      iter_tmp = combo_model.get_iter_first()
      while True:
        s_tmp = str(combo_model.get_value(iter_tmp, 0))
        if s_tmp == OPTION_TEXT_COMBOBOX:
          break

        # chosing range's column  
        if column == 2:
          l_tmp.append(s_tmp.split('-')[0].strip())
          l_tmp.append(s_tmp.split('-')[1].strip())
        else: # other column
          l_tmp.append(s_tmp)

        iter_tmp = combo_model.iter_next(iter_tmp)

################ FIRST STEP FOR MAKING TEST OF INPUT DATA ##############
      if s_sub == '':
        return
      # detecting existing dict of s_host
      try:
        self.our_parser.d_subnets[s_sub] == None
      except:
        self.our_parser.d_subnets[s_sub] = { }
      print l_tmp
      self.our_parser.d_subnets[s_sub][s_column_title] = l_tmp

  # this func is handler events of editing cells
  def edited_table(self, cell, row, user_data, model, column, type_table):
    b_run = False
    b_hrange_from = False
    b_hrange_to = False
    iter_some = None
    b_srange_from = False
    b_srange_to = False

    if type_table != GENERAL_TYPE_TABLE and user_data != '' and column == 0:
      # for adding a new item
      # fill columns which are for range
      if type_table == HOSTS_TYPE_TABLE:
        l_tmp = ['']
        for i in range(COUNT_COLUMN_HOSTS - 1 + 2): # 2 - because range require 3 column
          if i == 2 or i == COUNT_COLUMN_HOSTS - 1 or i == COUNT_COLUMN_HOSTS - 1 + 1 or i == 3:
            l_tmp.append(OPTION_TEXT_COMBOBOX)
          else:
            l_tmp.append('')
        model.append(l_tmp)
      elif type_table == SUBNETS_TYPE_TABLE:
        l_tmp = ['']
        for i in range(COUNT_COLUMN_SUBNETS - 1 + 2): # 2 - because range require 3 column
          if i == 1 or i == COUNT_COLUMN_SUBNETS - 1 or i == COUNT_COLUMN_SUBNETS - 1 + 1:
            l_tmp.append(OPTION_TEXT_COMBOBOX)
          else:
            l_tmp.append('')
        model.append(l_tmp)

    # detecting range's cells and save this information
    if self.builder.get_object("subnetscellrenderertext3_1") == cell:
      b_srange_from = True
      combo_model = self.builder.get_object("for_subnets_range")
      iter_some = self.iter_combo_srange
    if self.builder.get_object("subnetscellrenderertext3_2") == cell:
      b_srange_to = True
      combo_model = self.builder.get_object("for_subnets_range")
      iter_some = self.iter_combo_srange
    # detecting range's cells and save this information
    if self.builder.get_object("hostscellrenderertext4_1") == cell:
      b_hrange_from = True
      combo_model = self.builder.get_object("for_hosts_range")
      iter_some = self.iter_combo_range
    if self.builder.get_object("hostscellrenderertext4_2") == cell:
      b_hrange_to = True
      combo_model = self.builder.get_object("for_hosts_range")
      iter_some = self.iter_combo_range

    # handling situation when working with first_combo_box
    if type_table == GENERAL_TYPE_TABLE and column == 4:
      combo_model = self.builder.get_object("for_combo")
      iter_some = self.iter_first_combo
      b_run = True
    # handling situation when working with first_hosts_fa
    if type_table == HOSTS_TYPE_TABLE and column == 4:
      combo_model = self.builder.get_object("for_hosts_fa")
      iter_some = self.iter_combo_fa
      b_run = True

    if b_hrange_from == True or b_hrange_to == True or b_srange_from == True or b_srange_to == True:
      if b_hrange_from == True:
        i_new_column = COUNT_COLUMN_HOSTS + 1 - 1
      elif b_hrange_to == True:
        i_new_column = COUNT_COLUMN_HOSTS + 2 - 1
      elif b_srange_from == True:
        i_new_column = COUNT_COLUMN_SUBNETS + 1 - 1
      elif b_srange_to == True:
        i_new_column = COUNT_COLUMN_SUBNETS + 2 - 1

      if model[row][i_new_column] == OPTION_TEXT_COMBOBOX and user_data != OPTION_TEXT_COMBOBOX:
        if user_data != '':
          # deleting OPTION_TEXT_COMBOBOX
          combo_model.remove(iter_some)
          iter_tmp = combo_model.get_iter_first()
          if b_hrange_from == True or b_srange_from == True:
            if model[row][i_new_column + 1] != OPTION_TEXT_COMBOBOX:
              combo_model.append([user_data + ' - ' + model[row][i_new_column + 1]])
            model[row][column] = user_data + ' - ' + model[row][i_new_column + 1]
          else:
            if model[row][i_new_column - 1] != OPTION_TEXT_COMBOBOX:
              combo_model.append([ model[row][i_new_column - 1] + ' - ' + user_data])
            model[row][column] = model[row][i_new_column - 1] + ' - ' + user_data
          # adding OPTION_TEXT_COMBOBOX
          # memorizing iterator of combo model to insert other items
          iter_some = combo_model.append([OPTION_TEXT_COMBOBOX])
      else:
        # finding our items
        iter_tmp = combo_model.get_iter_first()
        for k in range(len(combo_model)):
          if combo_model.get_value(iter_tmp, 0) == model[row][column] and model[row][column] != OPTION_TEXT_COMBOBOX:
            # deleting item when user enter empty string
            combo_model.remove(iter_tmp)
            if user_data == '':
              if b_hrange_from == True or b_hrange_to == True:
                model[row][COUNT_COLUMN_HOSTS + 1 - 1] = OPTION_TEXT_COMBOBOX
                model[row][COUNT_COLUMN_HOSTS + 2 - 1] = OPTION_TEXT_COMBOBOX
              elif b_srange_from == True or b_srange_to == True:
                model[row][COUNT_COLUMN_SUBNETS + 1 - 1] = OPTION_TEXT_COMBOBOX
                model[row][COUNT_COLUMN_SUBNETS + 2 - 1] = OPTION_TEXT_COMBOBOX

              model[row][column] = OPTION_TEXT_COMBOBOX
              break

            if user_data != '':
              # deleting OPTION_TEXT_COMBOBOX
              combo_model.remove(iter_some)
              if b_hrange_from == True or b_srange_from == True:
                combo_model.append([user_data + ' - ' + model[row][i_new_column + 1]])
                model[row][column] = user_data + ' - ' + model[row][i_new_column + 1]
              else:
                combo_model.append([ model[row][i_new_column - 1] + ' - ' + user_data])
                model[row][column] = model[row][i_new_column - 1] + ' - ' + user_data
              # adding OPTION_TEXT_COMBOBOX
              # memorizing iterator of combo model to insert other items
              iter_some = combo_model.append([OPTION_TEXT_COMBOBOX])
            break
          else:
            iter_tmp = combo_model.iter_next(iter_tmp)

    if b_run == True:
      if model[row][column] == OPTION_TEXT_COMBOBOX and user_data != OPTION_TEXT_COMBOBOX:
        if user_data != '':
          # deleting OPTION_TEXT_COMBOBOX
          combo_model.remove(iter_some)
          combo_model.append([user_data])
          # adding OPTION_TEXT_COMBOBOX
          # memorizing iterator of combo model to insert other items
          iter_some = combo_model.append([OPTION_TEXT_COMBOBOX])
      else:
        # finding our items
        iter_tmp = combo_model.get_iter_first()
        for k in range(len(combo_model)):
          if combo_model.get_value(iter_tmp, 0) == model[row][column] and model[row][column] != OPTION_TEXT_COMBOBOX:
            combo_model.remove(iter_tmp)
            # deleting item when user enter empty string
            if user_data != '':
              # deleting OPTION_TEXT_COMBOBOX
              combo_model.remove(iter_some)
              combo_model.append([user_data])
              # adding OPTION_TEXT_COMBOBOX
              # memorizing iterator of combo model to insert other items
              iter_some = combo_model.append([OPTION_TEXT_COMBOBOX])
            break
          else:
            iter_tmp = combo_model.iter_next(iter_tmp)

    # memorizing last iterator
    if type_table == GENERAL_TYPE_TABLE and column == 4:
      self.iter_first_combo = iter_some
    if type_table == HOSTS_TYPE_TABLE and column == 4:
      self.iter_combo_fa = iter_some
    if type_table == HOSTS_TYPE_TABLE and column == 3:
      self.iter_combo_range = iter_some
    if type_table == SUBNETS_TYPE_TABLE and column == 2:
      self.iter_combo_srange = iter_some

############ TEST IT !!!!!!!!!!!!!!!!! ##################################
    if b_run == True or b_hrange_from == True or b_hrange_to == True or b_srange_from == True or b_srange_to == True:
      # memorizing data in common dictionary
      self.memorize_data_in_common_dict(row, column, model, combo_model, type_table)
###########################################################################

    if user_data != '':
      # changing a cell
      if b_hrange_from == True: # first cell of host's range
        model[row][COUNT_COLUMN_HOSTS + 1 - 1] = user_data
        if model[row][column] != OPTION_TEXT_COMBOBOX:
          model[row][column] = user_data + ' - ' + model[row][column].split('-')[1].strip()
        else:
          model[row][column] = OPTION_TEXT_COMBOBOX

      elif b_hrange_to == True: # second cell of host's range
        model[row][COUNT_COLUMN_HOSTS + 2 - 1] = user_data
        if model[row][column] != OPTION_TEXT_COMBOBOX:
          model[row][column] = model[row][column].split('-')[0].strip() + ' - ' + user_data
        else:
          model[row][column] = OPTION_TEXT_COMBOBOX

      elif b_srange_from == True: # first cell of subnet's range
        model[row][COUNT_COLUMN_SUBNETS + 1 - 1] = user_data
        if model[row][column] != OPTION_TEXT_COMBOBOX:
          model[row][column] = user_data + ' - ' + model[row][column].split('-')[1].strip()
        else:
          model[row][column] = OPTION_TEXT_COMBOBOX

      elif b_srange_to == True: # second cell of subnet's range
        model[row][COUNT_COLUMN_SUBNETS + 2 - 1] = user_data
        if model[row][column] != OPTION_TEXT_COMBOBOX:
          model[row][column] = user_data + ' - ' + model[row][column].split('-')[1].strip()
        else:
          model[row][column] = OPTION_TEXT_COMBOBOX

      else: # other cell
        model[row][column] = user_data
    elif b_run == True:
      model[row][column] = OPTION_TEXT_COMBOBOX
    else:
      model[row][column] = ''


  # convert from list to pattern of string
  def parser_from_list_single(self, l_something):
    s_something = ''
    for word in l_something:
      s_something = s_something + word + ',  '
    return s_something[0: len( s_something ) - 3]


  # convert from list to pattern of string
  def parser_from_list_twice(self, l_something):
    s_something = ''
    for k in range(len(l_something)):
      s_something = s_something + l_something[k]
      if (k + 1) % 2 == 0:
        s_something = s_something + ';  '
      else:
        s_something = s_something + '  -  '
    return s_something

  # from dict to liststore for global parameters 
  def fill_general_table(self, d_global_param):
    for i in range(COUNT_COLUMN_GENERAL):
      string = 'generaltreeviewcolumn' + str(i+1)
      general_liststore = self.builder.get_object("for_general")
      s_column_title = self.builder.get_object(string).get_title()

      if s_column_title == 'option domain-name-servers':
        try:
          l_tmp_data = self.parser_from_list_single( d_global_param[ s_column_title ] ).split(',')
          general_liststore[0][i] = l_tmp_data[0]
        except:
          # catch situation when parameter is empty
          l_tmp_data = [ ]
          general_liststore[0][i] = OPTION_TEXT_COMBOBOX

        # working with CellRendererCombo
        combo_model = self.builder.get_object("for_combo")
        for s_something in l_tmp_data:
          combo_model.append([s_something.strip()])

        # adding OPTION_TEXT_COMBOBOX
        # memorizing iterator of combo model to insert other items
        self.iter_first_combo = combo_model.append([OPTION_TEXT_COMBOBOX])

        combo_box = self.builder.get_object("generalcellrenderercombo5")
        combo_box.set_property("model", combo_model)
      else:
        try:
          general_liststore[0][i] =  d_global_param[ s_column_title ]
        except:
          general_liststore[0][i] = ''

  # from dict to liststore for hosts
  def fill_hosts_table(self, d_hosts_param):
    hosts_liststore = self.builder.get_object("for_hosts")
    i = 0
    for host in d_hosts_param:
      hosts_liststore.append(['', '', '', '', '', '', '', ''])
      for j in range(COUNT_COLUMN_HOSTS):
        string = 'hoststreeviewcolumn' + str(j + 1)
        s_column_title = self.builder.get_object(string).get_title()

        if s_column_title == 'fixed-address':
          try:
            hosts_liststore[i][j] = self.parser_from_list_single( d_hosts_param[host][ s_column_title ] )
          except:
            hosts_liststore[i][j] = ''

          try:
            l_tmp_data = self.parser_from_list_single( d_hosts_param[host][ s_column_title ] ).split(',')
            hosts_liststore[i][j] = l_tmp_data[0]
          except:
            # catch situation when parameter is empty
            l_tmp_data = [ ]
            hosts_liststore[i][j] = OPTION_TEXT_COMBOBOX

#          if i == 0:
            # working with CellRendererCombo
          combo_model = self.builder.get_object("for_hosts_fa")
#            for s_something in l_tmp_data:
#              combo_model.append([s_something.strip()])

            # adding OPTION_TEXT_COMBOBOX
            # memorizing iterator of combo model to insert other items
          self.iter_combo_fa = combo_model.append([OPTION_TEXT_COMBOBOX])

          combo_box = self.builder.get_object("hostscellrenderercombo5")
          combo_box.set_property("model", combo_model)

        elif s_column_title == 'range':
          try:
            l_tmp_data = self.parser_from_list_single( d_hosts_param[host][ s_column_title ] ).split(';')
            l_tmp_data = l_tmp_data[0].split(',')
            hosts_liststore[i][j] = l_tmp_data[0].strip() + ' - ' + l_tmp_data[1].strip()

            hosts_liststore[i][COUNT_COLUMN_HOSTS + 1 - 1] = l_tmp_data[0].strip()
            hosts_liststore[i][COUNT_COLUMN_HOSTS + 2 - 1] = l_tmp_data[1].strip()
          except:
            # catch situation when parameter is empty
            l_tmp_data = [ ]
            hosts_liststore[i][j] = OPTION_TEXT_COMBOBOX
            hosts_liststore[i][COUNT_COLUMN_HOSTS + 1 - 1] = OPTION_TEXT_COMBOBOX
            hosts_liststore[i][COUNT_COLUMN_HOSTS + 2 - 1] = OPTION_TEXT_COMBOBOX

          # working with CellRendererCombo
          combo_model = self.builder.get_object("for_hosts_range")

          # adding OPTION_TEXT_COMBOBOX
          # memorizing iterator of combo model to insert other items
          self.iter_combo_range = combo_model.append([OPTION_TEXT_COMBOBOX])

          combo_box = self.builder.get_object("hostscellrenderercombo4")
          combo_box.set_property("model", combo_model)
        else:
          try:
            hosts_liststore[i][j] = d_hosts_param[host][ s_column_title ]
          except:
            hosts_liststore[i][j] = ''

      hosts_liststore[i][0] = host
      i = i + 1
    # for adding a new host
    # fill columns which are for range or fixed-address
    # the other columns are empty 
    l_tmp = ['']
    for i in range(COUNT_COLUMN_HOSTS - 1 + 2): # 2 - because range require 3 column
      if i == 2 or i == COUNT_COLUMN_HOSTS - 1 or i == COUNT_COLUMN_HOSTS - 1 + 1 or i == 3:
        l_tmp.append(OPTION_TEXT_COMBOBOX)
      else:
        l_tmp.append('')
    hosts_liststore.append(l_tmp)


  # from dict to liststore for subnets
  def fill_subnets_table(self, d_subnets_param):
    subnets_liststore = self.builder.get_object("for_subnets")
    i = 0
    for sub in d_subnets_param:
      subnets_liststore.append(['', '', '', '', '', '', ''])
      for j in range(COUNT_COLUMN_SUBNETS):
        string = 'subnetstreeviewcolumn' + str(j + 1)

        s_column_title = self.builder.get_object(string).get_title()

        if s_column_title == 'range':
          try:
            l_tmp_data = self.parser_from_list_single( d_subnets_param[sub][ s_column_title ] ).split(';')
            l_tmp_data = l_tmp_data[0].split(',')
            subnets_liststore[i][j] = l_tmp_data[0].strip() + ' - ' + l_tmp_data[1].strip()

            subnets_liststore[i][COUNT_COLUMN_SUBNETS + 1 - 1] = l_tmp_data[0].strip()
            subnets_liststore[i][COUNT_COLUMN_SUBNETS + 2 - 1] = l_tmp_data[1].strip()
          except:
            # catch situation when parameter is empty
            l_tmp_data = [ ]
            subnets_liststore[i][j] = OPTION_TEXT_COMBOBOX
            subnets_liststore[i][COUNT_COLUMN_SUBNETS + 1 - 1] = OPTION_TEXT_COMBOBOX
            subnets_liststore[i][COUNT_COLUMN_SUBNETS + 2 - 1] = OPTION_TEXT_COMBOBOX

          # working with CellRendererCombo
          combo_model = self.builder.get_object("for_subnets_range")

          # adding OPTION_TEXT_COMBOBOX
          # memorizing iterator of combo model to insert other items
          self.iter_combo_srange = combo_model.append([OPTION_TEXT_COMBOBOX])

          combo_box = self.builder.get_object("subnetscellrenderercombo3")
          combo_box.set_property("model", combo_model)

        else:
          try:
            subnets_liststore[i][j] = d_subnets_param[sub][ s_column_title ]
          except:
            subnets_liststore[i][j] = ''

      name_netmask = sub.split(':')
      subnets_liststore[i][0] = name_netmask[0]
      subnets_liststore[i][1] = name_netmask[1]
      i = i + 1
    # for adding a new host
    # fill columns which are in range
    # the other columns are empty
    l_tmp = ['']
    for i in range(COUNT_COLUMN_SUBNETS - 1 + 2): # 2 - because range require 3 column
      if i == 1 or i == COUNT_COLUMN_SUBNETS - 1 or i == COUNT_COLUMN_SUBNETS - 1 + 1:
        l_tmp.append(OPTION_TEXT_COMBOBOX)
      else:
        l_tmp.append('')
    subnets_liststore.append(l_tmp)

  # func is for test some event
  def save(self, widget):
#    self.print_to_file(sys.argv[1], self.get_global_dict_from_cells(), self.get_subnets_dict_from_cells(), self.get_hosts_dict_from_cells())
    self.print_to_file("new_new_out.txt", self.get_global_dict_from_cells(), self.get_subnets_dict_from_cells(), self.get_hosts_dict_from_cells())


  def start(self, widget):
    os.system("service isc-dhcp-server start")


  def restart(self, widget):
    os.system("service isc-dhcp-server restart")


  def stop(self, widget):
    os.system("service isc-dhcp-server stop")


  # func is for setting handlers
  def set_handlers_cells(self, count_column, s_name_ren, s_name_liststore, type_table):
    liststore = self.builder.get_object(s_name_liststore)
    for i in range(count_column):
      if (i + 1 == NUMBER_HOSTS_RANGE and type_table == HOSTS_TYPE_TABLE) or (i + 1 == NUMBER_SUBNETS_RANGE and type_table == SUBNETS_TYPE_TABLE):
        string = s_name_ren + str(i + 1) + '_1'
        self.builder.get_object(string).connect('edited', self.edited_table, liststore, i, type_table)
        string = s_name_ren + str(i + 1) + '_2'
        self.builder.get_object(string).connect('edited', self.edited_table, liststore, i, type_table)
      else:
        string = s_name_ren + str(i + 1)
        self.builder.get_object(string).connect('edited', self.edited_table, liststore, i, type_table)


  def cellcombo_edited(self, cellrenderer, path, new_text):
    treeviewgeneral = self.builder.get_object("treeviewgeneral")
    treeviewmodel = treeviewgeneral.get_model()
    iter = treeviewmodel.get_iter(path)
    treeviewmodel.set_value(iter, 4, new_text)


  def cellcombo_edited_hfa(self, cellrenderer, path, new_text):
    treeviewgeneral = self.builder.get_object("treeviewhosts")
    treeviewmodel = treeviewgeneral.get_model()
    iter = treeviewmodel.get_iter(path)
    treeviewmodel.set_value(iter, 4, new_text)


  def cellcombo_edited_hrange(self, cellrenderer, path, new_text):
    treeviewgeneral = self.builder.get_object("treeviewhosts")
    treeviewmodel = treeviewgeneral.get_model()
    iter = treeviewmodel.get_iter(path)
    treeviewmodel.set_value(iter, 3, new_text)
    if new_text != OPTION_TEXT_COMBOBOX and new_text != None:
      treeviewmodel.set_value(iter, COUNT_COLUMN_HOSTS + 1 - 1, new_text.split('-')[0].strip())
      treeviewmodel.set_value(iter, COUNT_COLUMN_HOSTS + 2 - 1, new_text.split('-')[1].strip())
    else:
      treeviewmodel.set_value(iter, COUNT_COLUMN_HOSTS + 1 - 1, OPTION_TEXT_COMBOBOX)
      treeviewmodel.set_value(iter, COUNT_COLUMN_HOSTS + 2 - 1, OPTION_TEXT_COMBOBOX)

  def cellcombo_edited_srange(self, cellrenderer, path, new_text):
    treeviewgeneral = self.builder.get_object("treeviewsubnets")
    treeviewmodel = treeviewgeneral.get_model()
    iter = treeviewmodel.get_iter(path)
    treeviewmodel.set_value(iter, 2, new_text)
    if new_text != OPTION_TEXT_COMBOBOX and new_text != None:
      treeviewmodel.set_value(iter, COUNT_COLUMN_SUBNETS + 1 - 1, new_text.split('-')[0].strip())
      treeviewmodel.set_value(iter, COUNT_COLUMN_SUBNETS + 2 - 1, new_text.split('-')[1].strip())
    else:
      treeviewmodel.set_value(iter, COUNT_COLUMN_SUBNETS + 1 - 1, OPTION_TEXT_COMBOBOX)
      treeviewmodel.set_value(iter, COUNT_COLUMN_SUBNETS + 2 - 1, OPTION_TEXT_COMBOBOX)




  def hosts_cell_click(self, selection, d_hosts_param):
################# PROBLEM!!!!!!!!!! ######################################
    # get number of row which is selected
    try:
      i_selected_row = selection.get_selected_rows()[1][0][0]
    except:
      return
###########################################################################
    model_table_hosts = self.builder.get_object("for_hosts")
    s_host = model_table_hosts[i_selected_row][0]
    for s_column_title in ["fixed-address", "range"]:

      # binding title and number of column for real name of column
      d_number_column = {
        "fixed-address" : ["5" , "for_hosts_fa"],
        "range" : ["4" , "for_hosts_range"]
      }

      try:
        l_tmp_data = self.parser_from_list_single( d_hosts_param[s_host][ s_column_title ] ).split(',')
      except:
        # catch situation when parameter is empty
        l_tmp_data = [ ]

      # working with CellRendererCombo
      combo_model = self.builder.get_object(d_number_column[s_column_title][1])
      combo_model.clear()

      # adding OPTION_TEXT_COMBOBOX
      # adding to model, which is rendered
      # and memorizing iterator of combo model to insert other items
      if d_number_column[s_column_title][1] == "for_hosts_fa":
        for s_something in l_tmp_data:
          combo_model.append([s_something.strip()])
        self.iter_combo_fa = combo_model.append([OPTION_TEXT_COMBOBOX])
      if d_number_column[s_column_title][1] == "for_hosts_range":
        for l in range(len(l_tmp_data)):
          if (l % 2) == 0:
            combo_model.append([l_tmp_data[l].strip() + ' - ' + l_tmp_data[l + 1].strip()])
        self.iter_combo_range = combo_model.append([OPTION_TEXT_COMBOBOX])

      combo_box = self.builder.get_object("hostscellrenderercombo" + d_number_column[s_column_title][0])
      combo_box.set_property("model", combo_model)



  def subnets_cell_click(self, selection, d_subnets_param):
################# PROBLEM!!!!!!!!!! ######################################
    # get number of row which is selected
    try:
      i_selected_row = selection.get_selected_rows()[1][0][0]
    except:
      return
###########################################################################
    model_table_subnets = self.builder.get_object("for_subnets")
    s_subnet = model_table_subnets[i_selected_row][0] + ':' + model_table_subnets[i_selected_row][1]
    for s_column_title in ["range"]:

      # binding title and number of column for real name of column
      d_number_column = {
        "range" : ["3" , "for_subnets_range"]
      }

      try:
        l_tmp_data = self.parser_from_list_single( d_subnets_param[s_subnet][ s_column_title ] ).split(',')
      except:
        # catch situation when parameter is empty
        l_tmp_data = [ ]

      # working with CellRendererCombo
      combo_model = self.builder.get_object( d_number_column[s_column_title][1] )
      combo_model.clear()

      # adding OPTION_TEXT_COMBOBOX
      # adding to model, which is rendered
      # and memorizing iterator of combo model to insert other items
      if d_number_column[s_column_title][1] == "for_subnets_range":
        for l in range(len(l_tmp_data)):
          if (l % 2) == 0:
            combo_model.append([l_tmp_data[l].strip() + ' - ' + l_tmp_data[l + 1].strip()])
        self.iter_combo_srange = combo_model.append([OPTION_TEXT_COMBOBOX])

      combo_box = self.builder.get_object("subnetscellrenderercombo" + d_number_column[s_column_title][0])
      combo_box.set_property("model", combo_model)


  # initialize Class
  def __init__(self):
    # here parsing file which has got from parameters of program
    self.our_parser = Parser()

    self.builder = gtk.Builder()
    self.builder.add_from_file("face.glade")

    self.window = self.builder.get_object("mainwindow")

    # set handlers for editing combobox option domain-name-servers
    firstcombobox = self.builder.get_object("generalcellrenderercombo5")
    firstcombobox.connect("edited", self.cellcombo_edited)

    # set handlers for editing combobox fixed-address
    firstcombobox = self.builder.get_object("hostscellrenderercombo5")
    firstcombobox.connect("edited", self.cellcombo_edited_hfa)

    # set handlers for editing combobox range of hosts
    firstcombobox = self.builder.get_object("hostscellrenderercombo4")
    firstcombobox.connect("edited", self.cellcombo_edited_hrange)

    # set handlers for editing combobox range of subnets
    firstcombobox = self.builder.get_object("subnetscellrenderercombo3")
    firstcombobox.connect("edited", self.cellcombo_edited_srange)

    # set handlers to detect row of treeviewhosts
    selection = self.builder.get_object("treeviewhosts").get_selection()
    selection.connect('changed', self.hosts_cell_click, self.our_parser.d_hosts)

    # set handlers to detect row of treeviewsubnets
    selection = self.builder.get_object("treeviewsubnets").get_selection()
    selection.connect('changed', self.subnets_cell_click, self.our_parser.d_subnets)

    # set handlers for something
    operation = {
      "on_exit" : self.exit,
      "on_save" : self.save,
      "on_start" : self.start,
      "on_restart" : self.restart,
      "on_stop" : self.stop
        }

    self.builder.connect_signals( operation )

    # set handlers for editing cells
    self.set_handlers_cells(COUNT_COLUMN_GENERAL, "generalcellrenderertext", "for_general", GENERAL_TYPE_TABLE)
    self.set_handlers_cells(COUNT_COLUMN_HOSTS, "hostscellrenderertext", "for_hosts", HOSTS_TYPE_TABLE)
    self.set_handlers_cells(COUNT_COLUMN_SUBNETS, "subnetscellrenderertext", "for_subnets", SUBNETS_TYPE_TABLE)

#    s_text_dhcp = self.our_parser.get_text_from_file( sys.argv[1] )
    s_text_dhcp = self.our_parser.get_text_from_file("../new_out.txt")

    self.our_parser.get_global_parameters_from_text( s_text_dhcp )
    self.fill_general_table( self.our_parser.d_global_parameters )

    self.our_parser.get_hosts_from_text(s_text_dhcp)
    self.fill_hosts_table( self.our_parser.d_hosts )

    self.our_parser.get_subnets_from_text(s_text_dhcp)
    self.fill_subnets_table( self.our_parser.d_subnets )



if __name__ == "__main__":
  main = Main()
  main.window.show()
  gtk.main()
