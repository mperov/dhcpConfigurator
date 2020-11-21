#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Author: Maxim Perov (coder@frtk.ru)

This program can help to configurate DHCP server.
It uses GUI which was made in Glade. ( ./face.glade )
To use this utility on your computer, you should edit NAME_DHCP_SERVICE.
This variable contains name of DHCP service which allows to start/restart/stop DHCP server.

When you run this program it requires path for file settings of DHCP server.
'''

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

# This variable is used to define service which works with DHCP server.
NAME_DHCP_SERVICE = "isc-dhcp-server"

class Prompt(Exception):
  ''' This class is generator WARNING window.'''
  def __init__(self, value):
    self.value = value
    # Create new GTK dialog with all the fixings
    prompt = gtk.MessageDialog(None, 0, gtk.MESSAGE_WARNING, gtk.BUTTONS_OK, value)
    # Set title of dialog
    prompt.set_title("Предупреждение")
    # Show all widgets in prompt
    prompt.show_all()
    # Run dialog until user clicks OK
    if prompt.run() == gtk.RESPONSE_OK:
      # Destory prompt
      prompt.destroy()

class Parser:
  '''This class is parser settings.
  Some method looks for some information in the text and gets dicts.'''
  digits = "0123456789"
  colon,semi,period,comma,lbrace,rbrace,quote = map(Literal,':;.,{}"')
  number = Word(digits)
  hexint = Word(hexnums,exact = 2)
  dnschars = Word(alphanums + '-') # characters permissible in DNS names

  mac = Combine(hexint + (":" + hexint) * 5)
  ip = Combine(Word(nums) + ('.' + Word(nums))*3)
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
    '''This method gets string which is similar to pattern.
    Keywords:
      l_some - list is contained words.
      pattern - similar string
    Returns:
      None
      but result is saved to self.d_hosts '''
    for s_word in l_some:
      grammar_word = pattern
      parse_word_results = grammar_word.searchString(s_word)
      for group in parse_word_results:
        self.d_hosts[l_some[1]][group[0]] = group[1]



  def get_hosts_from_text(self, s_text_dhcp):
    '''This method searches hosts and gets dict, which contains hosts.
    Keywords:
      s_text_dhcp - text settings dhcp server. 
    Returns:
      None
      but dict is placed in d_hosts of Parser.'''
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
    ''' This method gets string which is similar to pattern.
    Keywords:
      l_some - list is contained words.
      pattern - similar string
    Returns:
      None
      but result is saved to self.d_subnets '''
    for s_word in l_some:
      grammar_word = StringStart() + Literal(s_pattern) + self.number
      parse_word_results = grammar_word.searchString(s_word)
      for group_dft in parse_word_results:
        self.d_subnets[l_some[1] + ':' + l_some[3]][group_dft[0]] = group_dft[1]


  
  def get_subnets_from_text(self, s_text_dhcp):
    ''' This method searches subnets and gets dict, which contains subnets.
    Keywords:
      s_text_dhcp - text settings dhcp server. 
    Returns:
      None
      but dict is placed in d_subnets of Parser. '''
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
    ''' This method gets string which is similar to pattern.
    Keywords:
      l_some - list is contained words.
      pattern - similar string
    Returns:
      None
      but result is saved to self.d_global_parameters '''
    parse_global_parameter = StringStart() + Literal(s_pattern) + pp_pattern
    parse_line_results = parse_global_parameter.searchString(s_some)
    if len(parse_line_results) > 0:
      self.d_global_parameters[parse_line_results[0][0]] = parse_line_results[0][1]

  
  def get_global_parameters_from_text(self, s_text_dhcp):
    ''' This method searches global parameters and gets dict, which contains global parameters.
    Keywords:
      s_text_dhcp - text settings dhcp server. 
    Returns:
      None
      but dict is placed in d_global_parameters of Parser. '''
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
    ''' This method gets text from file. '''
    f_dhcp = open(s_file_name, 'rU')
    return f_dhcp.read()


class Main:
  '''This class contains handlers some events, 
  some functiones which maps dict to table and back and
  method is printed settings to file. '''

  builder = None
  s_text_dhcp = ''
  iter_first_combo = None
  iter_combo_fa = None
  our_parser = None
  iter_combo_range = None
  iter_combo_srange = None

  
  def exit(self, widget):
    ''' Handler exit from program. '''
    sys.exit(0)

  
  def print_to_file(self, s_file_name, d_global_parameters, d_subnets, d_hosts):
    ''' This method printes all dicts to file.
    Keywords:
      s_file_name - name of output file.
      d_* - dicts which are printed to file
    Returns:
      None '''
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


  
  def get_global_dict_from_cells(self):
    ''' This method gets dict, which contains global parameters.
      It doesn't only gets from cells and it gets from for_combo.
      It is necessary to get option domain-name-servers.
    Keywords:
      None
    Returns:
      dict containing global parameters '''
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

	
  
  def get_hosts_dict_from_cells(self):
    ''' This method gets dict, which contains parameters of hosts.
      It doesn't only gets from cells and it gets from Parser::d_hosts.
      It is necessary to get fixed-address and range.
    Keywords:
      None
    Returns:
      dict containing parameters of hosts '''
    d_hosts_param = { }
    hosts_liststore = self.builder.get_object("for_hosts")
    i = 0
    host = self.builder.get_object('hoststreeviewcolumn1').get_title()
    while ( hosts_liststore[i][0].strip() != ''):
      d_hosts_param[ hosts_liststore[i][0] ] = { }
      for j in range(COUNT_COLUMN_HOSTS - 1):
        string = 'hoststreeviewcolumn' + str(j + 2)
        s_column_title = self.builder.get_object(string).get_title()
        if hosts_liststore[i][j + 1].strip() != '':
          if s_column_title == 'fixed-address' or s_column_title == 'range':
            if hosts_liststore[i][j+1].strip() != OPTION_TEXT_COMBOBOX:
              d_hosts_param[ hosts_liststore[i][0] ][s_column_title] = self.our_parser.d_hosts[ hosts_liststore[i][0] ][s_column_title]
            else:
              try: # catching situation when it's empty and host_liststore has OPTION_TEXT_COMBOBOX
                d_hosts_param[ hosts_liststore[i][0] ][s_column_title] = self.our_parser.d_hosts[ hosts_liststore[i][0] ][s_column_title]
              except:
                ''' nothing '''
          else:
            d_hosts_param[ hosts_liststore[i][0] ][s_column_title] = hosts_liststore[i][j+1]
      i = i + 1
    return d_hosts_param


  
  def get_subnets_dict_from_cells(self):
    ''' This method gets dict, which contains parameters of subnets.
      It doesn't only gets from cells and it gets from Parser::d_subnets.
      It is necessary to get range.
    Keywords:
      None
    Returns:
      dict containing parameters of subnets '''
    d_subnets_param = { }
    subnets_liststore = self.builder.get_object("for_subnets")
    i = 0
    sub = self.builder.get_object('subnetstreeviewcolumn1').get_title()
    while ( subnets_liststore[i][0].strip() != ''):
      d_subnets_param[ subnets_liststore[i][0] + ':' + subnets_liststore[i][1] ] = { }
      for j in range(COUNT_COLUMN_SUBNETS - 2):
        string = 'subnetstreeviewcolumn' + str(j + 3)
        s_column_title = self.builder.get_object(string).get_title()
        if subnets_liststore[i][j + 2].strip() != '':
          if s_column_title == 'range':
            if subnets_liststore[i][j + 2].strip() != OPTION_TEXT_COMBOBOX:
              d_subnets_param[ subnets_liststore[i][0] + ':' + subnets_liststore[i][1] ][s_column_title] = self.our_parser.d_subnets[ subnets_liststore[i][0] + ':' + subnets_liststore[i][1] ][s_column_title]
            else:
              try:# catching situation when it's empty and subnets_liststore has OPTION_TEXT_COMBOBOX
                d_subnets_param[ subnets_liststore[i][0] + ':' + subnets_liststore[i][1] ][s_column_title] = self.our_parser.d_subnets[ subnets_liststore[i][0] + ':' + subnets_liststore[i][1] ][s_column_title]
              except:
                ''' nothing '''
          else:
            d_subnets_param[ subnets_liststore[i][0] + ':' + subnets_liststore[i][1] ][s_column_title] = subnets_liststore[i][j + 2]
      i = i + 1
    return d_subnets_param


  
  def memorize_data_in_common_dict(self, row, column, model, combo_model, type_table):
    ''' This method saves special parameters in dicts of Parser
      e.g. range, fixed-address, etc.
      This method is only used by edited_table.
    Keywords:
      row, column - coordinates of place in model of liststore
      model - model of liststore
      combo_model - model of cellcombobox
      type_table - type of liststore
    Returns:
      None '''
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

      if s_host == '':
        return
      if l_tmp:
        # detecting existing dict of s_host
        try:
          if self.our_parser.d_hosts[s_host] == None:
            self.our_parser.d_hosts[s_host] = { }
        except:
          self.our_parser.d_hosts[s_host] = { }
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

      if s_sub == '':
        return

      if l_tmp:
        # detecting existing dict of s_host
        try:
          if self.our_parser.d_subnets[s_sub] == None:
            self.our_parser.d_subnets[s_sub] = { }
        except:
          self.our_parser.d_subnets[s_sub] = { }
        self.our_parser.d_subnets[s_sub][s_column_title] = l_tmp

 
  
  def add2table_liststore(self, model, combo_model, row, column, user_data, iter_some):
    ''' This method is for fixed-address or option domain-name-servers.
      It addes something to liststore and its cellcombobox.
      This is only used by edited_table.
    Keywords arduments:
      model - model of liststore
      combo_model - model of cellcombobox
      row, column - coordinates of place in model of liststore
      user_data - this is added by this method
      iter_some - position of iterator of cellcombobox 
    Returns:
      iterator of cellcombobox '''
    if model[row][column] == OPTION_TEXT_COMBOBOX and user_data != OPTION_TEXT_COMBOBOX:
      if user_data != '':
        # deleting OPTION_TEXT_COMBOBOX
        combo_model.remove(iter_some)
        combo_model.append([user_data])
        # adding OPTION_TEXT_COMBOBOX
        # memorizing iterator of combo model to insert other items
        return combo_model.append([OPTION_TEXT_COMBOBOX])
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
            return combo_model.append([OPTION_TEXT_COMBOBOX])
          break
        else:
          iter_tmp = combo_model.iter_next(iter_tmp)


  
  def add2table_for_ffc(self, row, column, model, user_data, i_column_place):
    ''' This method addes something to the first face cell of range and to cell for cellcombobox.
      This is only used by edited_table.
    Keywords arduments:
      row, column - coordinates of place in model of liststore
      model - model of liststore
      user_data - this is added by this method
      i_column_place - face coordinate of cell in model of liststore
    Returns:
      None '''
    model[row][i_column_place + 1 - 1] = user_data
    if model[row][column] != OPTION_TEXT_COMBOBOX:
      model[row][column] = user_data + ' - ' + model[row][column].split('-')[1].strip()
    else:
      model[row][column] = OPTION_TEXT_COMBOBOX


  
  def add2table_for_sfc(self, row, column, model, user_data, i_column_place):
    ''' This method addes something to the second face cell of range and to cell for cellcombobox.
      This is only used by edited_table.
    Keywords arduments:
      row, column - coordinates of place in model of liststore
      model - model of liststore
      user_data - this is added by this method
      i_column_place - face coordinate of cell in model of liststore
    Returns:
      None '''
    model[row][i_column_place + 2 - 1] = user_data
    if model[row][column] != OPTION_TEXT_COMBOBOX:
      model[row][column] = model[row][column].split('-')[0].strip() + ' - ' + user_data
    else:
      model[row][column] = OPTION_TEXT_COMBOBOX


  
  def add_row_for_new(self, model, type_table):
    ''' This method addes a new item to liststore, when user add a new host or subnet.
      and fill columns which are for range or the other
      This is only used by edited_table.
    Keywords:
      model - model of liststore
      type_table - type of liststore 
    Returns:
      None '''
    if type_table == HOSTS_TYPE_TABLE:
      l_tmp = ['']
      for i in range(COUNT_COLUMN_HOSTS - 1 + 2): # 2 - because range requires 3 column
        if i == 2 or i == COUNT_COLUMN_HOSTS - 1 or i == COUNT_COLUMN_HOSTS - 1 + 1 or i == 3:
          l_tmp.append(OPTION_TEXT_COMBOBOX)
        else:
          l_tmp.append('')
      model.append(l_tmp)
    elif type_table == SUBNETS_TYPE_TABLE:
      l_tmp = ['']
      for i in range(COUNT_COLUMN_SUBNETS - 1 + 2): # 2 - because range requires 3 column
        if i == 1 or i == COUNT_COLUMN_SUBNETS - 1 or i == COUNT_COLUMN_SUBNETS - 1 + 1:
          l_tmp.append(OPTION_TEXT_COMBOBOX)
        else:
          l_tmp.append('')
      model.append(l_tmp)


  
  def get_cellcombobox(self, s_name_object):
    ''' This method gets cellcombobox and iterator of last position.
      This is only used by edited_table.
    Keywords:
      s_name_object - name of cellcombobox object
    Returns:
      b_'some name' - everytime True
      cellcombobox
      iterator of cellcombobox '''
    iter_some = None
    if s_name_object == 'for_subnets_range':
      iter_some = self.iter_combo_srange
    elif s_name_object == 'for_hosts_range':
      iter_some = self.iter_combo_range
    elif s_name_object == 'for_combo':
      iter_some = self.iter_first_combo
    elif s_name_object == 'for_hosts_fa':
      iter_some = self.iter_combo_fa
    return True, self.builder.get_object(s_name_object), iter_some


  
  def test_correct_input(self, column, type_table, string):
    ''' This method tests input string.
    Keywords:
      column - one of coordinates of place in model of liststore
      type_table - type of liststore
      string - input string which is tested by this method.
    Returns:
      True - when input string is correct, False - when input string is incorrect. '''
    # check table of SUBNETS
    if type_table == SUBNETS_TYPE_TABLE:
      if column < 3: # all columns from 0 to 2 which are ip address
        if self.check_string_use_pattern(string, StringStart() + self.our_parser.ip + StringEnd()) == '':
          if string != OPTION_TEXT_COMBOBOX:
            try:
              raise Prompt('Вы ввели некорректные данные!\nПример коррекного ввода: 127.0.0.1')
            except:
              return False
      if column == 3 or column == 4:
        if self.check_string_use_pattern(string, StringStart() + self.our_parser.number + StringEnd()) == '':
          try:
            raise Prompt('Вы ввели некорректные данные!\nПример коррекного ввода: 7200')
          except:
            return False

    # check table of HOSTS
    if type_table == HOSTS_TYPE_TABLE:
      if column == 1: # check cell of mac address
        if self.check_string_use_pattern(string, StringStart() + self.our_parser.mac + StringEnd()) == '':
          try:
            raise Prompt('Вы ввели некорректные данные!\nПример коррекного ввода: 00:f5:12:00:01:a1')
          except:
            return False
      if column == 3 or column == 4: # they are ip address
        if self.check_string_use_pattern(string, StringStart() + self.our_parser.ip + StringEnd()) == '':
          if string != OPTION_TEXT_COMBOBOX:
            try:
              raise Prompt('Вы ввели некорректные данные!\nПример коррекного ввода: 127.0.0.1')
            except:
              return False

    # check table of GENERAL
    if type_table == GENERAL_TYPE_TABLE:
      if column == 2 or column == 3:
        if self.check_string_use_pattern(string, StringStart() + self.our_parser.number + StringEnd()) == '':
          try:
            raise Prompt('Вы ввели некорректные данные!\nПример коррекного ввода: 7200')
          except:
            return False

    return True


  
  def check_string_use_pattern(self, string, pattern):
    ''' This method checks the similarity of the pattern. 
      Pattern is got from class Parser.
    Keywords: 
      string - input string
      pattern - pattern of correct string
    Returns:
      if string is correct then method will return it
      else it will return '' '''
    s_parse_result = pattern.searchString(string)
    if s_parse_result:
      return s_parse_result[0][0]
    else:
      return ''


  
  def delete_row(self, model, row, type_table):
    ''' This method is deleter row, when first column is empry.
      This is only used by edited_table.
    Keywords:
      model - model of liststore
      row - row is needed to delete
      type_table - type of liststore
    Returns:
      None '''
    if type_table == HOSTS_TYPE_TABLE:
      i_max_column = COUNT_COLUMN_HOSTS
    else:
      i_max_column = COUNT_COLUMN_SUBNETS
    iter_last_row = model.get_iter_from_string(row)
    model.remove(iter_last_row)


  
  def edited_table(self, cell, row, user_data, model, column, type_table):
    ''' This method is handler events of editing cells.
      This method makes many interesting things!!!!!!!!!
    Keywords arduments:
      row - one of coordinates of place in model of liststore
      user_data - this is added by this method
      model - model of liststore
      combo_model - model of cellcombobox
      column - one of coordinates of place in model of liststore
      type_table - type of liststore 
    Returns: 
      None '''
    b_run = False
    b_hrange_from = False
    b_hrange_to = False
    iter_some = None
    b_srange_from = False
    b_srange_to = False
 
    # catching event when name of host or subnet is empty
    if column != 0 and model[row][0] == '':
      if user_data != '' and user_data != OPTION_TEXT_COMBOBOX:
        try:
          raise Prompt('Вначале необходимо заполнить\nпервый столбец!')
        except:
          return
    
    # catching event when mask of subnet is empty
    if type_table == SUBNETS_TYPE_TABLE and column != 0 and column != 1 and model[row][1] == '':
      if user_data != '' and user_data != OPTION_TEXT_COMBOBOX:
        try:
          raise Prompt('Также необходимо заполнить\nвторой столбец!')
        except:
          return
    # finding incorrect data
    if user_data != '' and self.test_correct_input(column, type_table, user_data) == False:
      return

    # clearing table without first column
    if column == 0 and user_data.strip() == '' and type_table != GENERAL_TYPE_TABLE and model[row][column] != '':
      self.delete_row(model, row, type_table)
      return

    # for adding a new item
    # fill columns which are for range or the other
    if type_table != GENERAL_TYPE_TABLE and user_data != '' and column == 0 and model[row][column] == '':
      self.add_row_for_new(model, type_table)

    # save a new host or subnet in global dict
    if type_table == HOSTS_TYPE_TABLE and column == 0 and user_data != model[row][column]:
      # memorizing data in common dictionary
      model[row][column] = user_data
      self.memorize_data_in_common_dict(row, 3, model, self.builder.get_object("for_hosts_range"), type_table)
      self.memorize_data_in_common_dict(row, 4, model, self.builder.get_object("for_hosts_fa"), type_table)
    elif type_table == SUBNETS_TYPE_TABLE and user_data != model[row][column]:
      if column == 0 or column == 1:
        # memorizing data in common dictionary
        model[row][column] = user_data
        self.memorize_data_in_common_dict(row, 2, model, self.builder.get_object("for_subnets_range"), type_table)

    # detecting range's cells and save this information
    if self.builder.get_object("subnetscellrenderertext3_1") == cell:
      b_srange_from, combo_model, iter_some = self.get_cellcombobox("for_subnets_range")
    if self.builder.get_object("subnetscellrenderertext3_2") == cell:
      b_srange_to, combo_model, iter_some = self.get_cellcombobox("for_subnets_range")

    # detecting range's cells and save this information
    if self.builder.get_object("hostscellrenderertext4_1") == cell:
      b_hrange_from, combo_model, iter_some = self.get_cellcombobox("for_hosts_range")
    if self.builder.get_object("hostscellrenderertext4_2") == cell:
      b_hrange_to, combo_model, iter_some = self.get_cellcombobox("for_hosts_range")

    # handling situation when working with first_combo_box
    if type_table == GENERAL_TYPE_TABLE and column == 4:
      b_run, combo_model, iter_some = self.get_cellcombobox("for_combo")
    # handling situation when working with first_hosts_fa
    if type_table == HOSTS_TYPE_TABLE and column == 4:
      b_run ,combo_model, iter_some = self.get_cellcombobox("for_hosts_fa")

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
      iter_some = self.add2table_liststore(model, combo_model, row, column, user_data, iter_some)

    # memorizing last iterator
    if type_table == GENERAL_TYPE_TABLE and column == 4:
      self.iter_first_combo = iter_some
    if type_table == HOSTS_TYPE_TABLE and column == 4:
      self.iter_combo_fa = iter_some
    if type_table == HOSTS_TYPE_TABLE and column == 3:
      self.iter_combo_range = iter_some
    if type_table == SUBNETS_TYPE_TABLE and column == 2:
      self.iter_combo_srange = iter_some

    if b_run == True or b_hrange_from == True or b_hrange_to == True or b_srange_from == True or b_srange_to == True:
      # memorizing data in common dictionary
      self.memorize_data_in_common_dict(row, column, model, combo_model, type_table)

    # changing a cell
    if user_data != '':
      if b_hrange_from == True: # first cell of host's range
        self.add2table_for_ffc(row, column, model, user_data, COUNT_COLUMN_HOSTS)
      elif b_hrange_to == True: # second cell of host's range
        self.add2table_for_sfc(row, column, model, user_data, COUNT_COLUMN_HOSTS)
      elif b_srange_from == True: # first cell of subnet's range
        self.add2table_for_ffc(row, column, model, user_data, COUNT_COLUMN_SUBNETS)
      elif b_srange_to == True: # second cell of subnet's range
        self.add2table_for_sfc(row, column, model, user_data, COUNT_COLUMN_SUBNETS)
      else: # other cell
        model[row][column] = user_data
    elif b_run == True or b_hrange_from == True or b_hrange_to == True or b_srange_from == True or b_srange_to == True:
      model[row][column] = OPTION_TEXT_COMBOBOX
    else:
      model[row][column] = ''


  
  def parser_from_list_single(self, l_something):
    ''' This method convertes from list to pattern of string.
      Divier in list words is ,
    Keywords:
      l_something - list is converted.
    Returns:
      resulting string '''
    s_something = ''
    for word in l_something:
      s_something = s_something + word + ',  '
    return s_something[0: len( s_something ) - 3]


  
  def parser_from_list_twice(self, l_something):
    ''' This method convertes from list to pattern of string.
      Diviers in list words are ; and -
    Keywords:
      l_something - list is converted.
    Returns:
      resulting string '''
    s_something = ''
    for k in range(len(l_something)):
      s_something = s_something + l_something[k]
      if (k + 1) % 2 == 0:
        s_something = s_something + ';  '
      else:
        s_something = s_something + '  -  '
    return s_something


  
  def fill_general_table(self, d_global_param):
    ''' This method fills general table. It gets parameters from dict and places them to liststore.
    Keywords:
      d_global_param - dict which contains global parameters.
    Returns:
      None '''
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


  
  def fill_hosts_table(self, d_hosts_param):
    ''' This method fills hosts table. It gets parameters from dict and places them to liststore.
    Keywords:
      d_hosts_param - dict which contains parameters of hosts.
    Returns:
      None '''
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

          # working with CellRendererCombo
          combo_model = self.builder.get_object("for_hosts_fa")

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

  
  def fill_subnets_table(self, d_subnets_param):
    ''' This method fills subnets table. It gets parameters from dict and places them to liststore.
    Keywords:
      d_subnets_param - dict which contains parameters of subnets.
    Returns:
      None '''
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


  
  def save(self, widget):
    ''' This method is handler event when user saves settings. '''
#    self.print_to_file(sys.argv[1], self.get_global_dict_from_cells(), self.get_subnets_dict_from_cells(), self.get_hosts_dict_from_cells())
    self.print_to_file("new_new_out.txt", self.get_global_dict_from_cells(), self.get_subnets_dict_from_cells(), self.get_hosts_dict_from_cells())
  
  
  def start(self, widget):
    ''' This method is handler event when user wishes to start DHCP server. '''
    os.system("service " + NAME_DHCP_SERVICE + " start")
  
  
  def restart(self, widget):
    ''' This method is handler event when user wishes to restart DHCP server. '''
    os.system("service " + NAME_DHCP_SERVICE + " restart")
  
  
  def stop(self, widget):
    ''' This method is handler event when user wishes to stop DHCP server.'''
    os.system("service " + NAME_DHCP_SERVICE + " stop")


  
  def set_handlers_cells(self, count_column, s_name_ren, s_name_liststore, type_table):
    ''' This method sets handlers for cells. 
    Keywords:
      count_column - count column at table
      s_name_ren - name of column 
      s_name_liststore - object name of liststore 
      type_table - type of liststore
    Returns:
      None '''
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
    ''' This method is handler event when user edites cellcombobox for option domain-name-servers.
    Keywords:
      cellrender - the object is edited.
      path - path to get iterator of cellcombobox
      new_text - text is added to cellcombobox '''
    treeviewgeneral = self.builder.get_object("treeviewgeneral")
    treeviewmodel = treeviewgeneral.get_model()
    iter = treeviewmodel.get_iter(path)
    treeviewmodel.set_value(iter, 4, new_text)


  
  def cellcombo_edited_hfa(self, cellrenderer, path, new_text):
    ''' This method is handler event when user edites cellcombobox for hosts fixed-address.
    Keywords:
      cellrender - the object is edited.
      path - path to get iterator of cellcombobox
      new_text - text is added to cellcombobox '''
    treeviewgeneral = self.builder.get_object("treeviewhosts")
    treeviewmodel = treeviewgeneral.get_model()
    iter = treeviewmodel.get_iter(path)
    treeviewmodel.set_value(iter, 4, new_text)


  
  def cellcombo_edited_hrange(self, cellrenderer, path, new_text):
    ''' This method is handler event when user edites cellcombobox for hosts range.
    Keywords:
      cellrender - the object is edited.
      path - path to get iterator of cellcombobox
      new_text - text is added to cellcombobox '''
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
    ''' This method is handler event when user edites cellcombobox for subnets range.
    Keywords:
      cellrender - the object is edited.
      path - path to get iterator of cellcombobox
      new_text - text is added to cellcombobox '''
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
    ''' This method is handler event when user click on table of hosts.
      It loads cellcomboboxes of fixed-address, range.
      Because each row has its fixed-address and range.
    Keywords:
      selection - it contains list of the tree paths of all selected rows.
      d_hosts_param - dict for parameters of hosts
    Returns:
      None '''

    # get number of row which is selected
    try:
      i_selected_row = selection.get_selected_rows()[1][0][0]
    except:
      return

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
          if (l % 2) == 0 and l_tmp_data[l] != '':
            combo_model.append([l_tmp_data[l].strip() + ' - ' + l_tmp_data[l + 1].strip()])
        self.iter_combo_range = combo_model.append([OPTION_TEXT_COMBOBOX])

      combo_box = self.builder.get_object("hostscellrenderercombo" + d_number_column[s_column_title][0])
      combo_box.set_property("model", combo_model)


  
  def subnets_cell_click(self, selection, d_subnets_param):
    ''' This method is handler event when user click on table of subnets.
      It loads cellcombobox of range.
      Because each row has its range.
    Keywords:
      selection - it contains list of the tree paths of all selected rows.
      d_hosts_param - dict for parameters of subnets
    Returns:
      None '''

    # get number of row which is selected
    try:
      i_selected_row = selection.get_selected_rows()[1][0][0]
    except:
      return

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
          if (l % 2) == 0 and l_tmp_data[l] != '':
            combo_model.append([l_tmp_data[l].strip() + ' - ' + l_tmp_data[l + 1].strip()])
        self.iter_combo_srange = combo_model.append([OPTION_TEXT_COMBOBOX])

      combo_box = self.builder.get_object("subnetscellrenderercombo" + d_number_column[s_column_title][0])
      combo_box.set_property("model", combo_model)


  
  def __init__(self):
    ''' Constructor of Main '''
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
    s_text_dhcp = self.our_parser.get_text_from_file("../out.txt")

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
