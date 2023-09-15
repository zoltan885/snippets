

import numpy as np
from dateutil.parser import parse
import os

class readfio():
    def __init__(self, fiofile):
        self.data = _fioparser(fn=fiofile)
        
        


def _fioparser(fn=None):
    lines = open(fn).read().splitlines()
    comment = []
    parameter = []
    data = {}
    datatmp = []
    columns = []
    cdatatype = []
    c = lines.index('%c')
    p = lines.index('%p')
    d = lines.index('%d')
    e = len(lines)-1
    
    for l in range(len(lines)):
        if lines[l].startswith('! Acquisition ended'):
            e = l

    for l in range(len(lines)):
        if not lines[l].startswith('!'):
            if l > c and l < p:
                comment.append(lines[l])
            if l > p and l < d:
                parameter.append(lines[l])
            if d < l < e:
                    if lines[l].split()[0] == 'Col':
                        columns.append(lines[l].split()[2])
                        cdatatype.append(lines[l].split()[3])
                    else:
                        datatmp.append([i for i in lines[l].split()])
    for i in range(len(columns)):
        if cdatatype[i].lower() in ['float', 'double']:
            data[columns[i]] = np.array(np.array(datatmp)[:,i], dtype=float)
        if cdatatype[i].lower() in ['string', 'integer']:
            data[columns[i]] = np.array(np.array(datatmp)[:,i], dtype=str)
    
    command = comment[0]
    print('Command: ', command)
    user = comment[1].split(' ')[1]
    print('User: ', user)
    date = parse(' '.join(comment[1].split(' ')[5:]))
    # get filedirs:
    savedir = {}
    for i in parameter:
        if 'filedir' in i.lower():
            channelNo = int(i.lower().partition('_')[0][7:])
            savedir['%d' % channelNo] = i.lower().rpartition(' = ')[2].replace('\\', '/').replace('t:/', 'gpfs/')

    print(savedir)
    return data



    


#    print('Date:', date.year, date.month, date.day, date.hour, date.minute, date.second)
    


class fioFile():
    def __init__(self, fiofile, nodata='NAN'):
        self.nodata = nodata
        self.sweep = False
        self._fioparser(fn=fiofile)
        if self.sweep:
            self._gen_file_list()
        print(self.sweep)


    def _fioparser(self, fn=None):
        lines = open(fn).read().splitlines()
        self.comment = []
        self.parameter = []
        self.data = {}
        datatmp = []
        columns = []
        cdatatype = []
        c = lines.index('%c')
        p = lines.index('%p')
        d = lines.index('%d')
        e = len(lines)-1
        
        for l in range(len(lines)):
            if lines[l].startswith('! Acquisition ended'):
                e = l

        for l in range(len(lines)):
            if not lines[l].startswith('!'):
                if l > c and l < p:
                    self.comment.append(lines[l])
                if l > p and l < d:
                    self.parameter.append(lines[l])
                if d < l < e:
                        if lines[l].split()[0] == 'Col':
                            columns.append(lines[l].split()[2])
                            cdatatype.append(lines[l].split()[3])
                        else:
                            datatmp.append([i for i in lines[l].split()])
        for i in range(len(columns)):
            if cdatatype[i].lower() in ['float', 'double']:
                try:
                    self.data[columns[i]] = np.array(np.array(datatmp)[:,i], dtype=float)
                except ValueError:
                    # handle nodata strings:
                    col = np.empty((len(np.array(datatmp)[:,i])))
                    if type(self.nodata) == str:
                        col[:] = np.nan
                    elif type(self.nodata) in [float, int]:
                        col[:] = self.nodata
                    for j,data in enumerate(np.array(datatmp)[:,i]):
                        try:
                            col[j] = np.float16(data)
                        except:
                            print('could not convert %s to float'% data)
                        else:
                            self.data[columns[i]] = col
                    print('nodata in data')
                except:
                    print('Exception')
            if cdatatype[i].lower() in ['string', 'integer']:
                self.data[columns[i]] = np.array(np.array(datatmp)[:,i], dtype=str)
        
        self.command = self.comment[0]
        if self.command.split(" ")[0] in ['fastsweep2', 'supersweep2', 'timesweep2']:
            self.sweep = True
        print('Command: ', self.command)
        self.user = self.comment[1].split(' ')[1]
        print('User: ', self.user)
        date = parse(' '.join(self.comment[1].split(' ')[5:]))
        # get filedirs:
        self.savedir = {}
        self.parameterdict = {}
        self.detectors = {}
        for par in self.parameter:
            k,v = par.split("=")[0].strip(), par.split("=")[1].strip()
            try:
                self.parameterdict[k] = float(v)
            except ValueError:  # if value is a dictionary
                if v[0] == "{" and v[-1] == "}":
                    #print('Dict found')
                    dct = {pp.strip(" ").replace("\"","").split(":")[0]:pp.strip(" ").replace("\"","").split(":")[1]   for pp in v.strip("{}").split(',')}
                    self.parameterdict[k] = dct
                    self.detectors[k] = dct
                else:
                    self.parameterdict[k] = v

            if 'filedir' in par.lower():
                pass
                #channelNo = int(par.lower().partition('_')[0][7:])
                #self.savedir['%d' % channelNo] = par.lower().rpartition(' = ')[2].replace('\\', '/').replace('t:/', 'gpfs/')

    def _gen_file_list(self):
        for k,v in self.detectors.items():
            path = v['Filedir']
            pattern = v['Filepattern'].strip(" ")
            extension = pattern.rpartition(".")[2]
            if extension in ['cbf', 'tif']:
                fileids = [int(i) for i in self.data[k]]
            elif extension in ['hdf']:
                fileids = [1]  # TODO: handle hdf files from Varex and Manta as well as from the Eiger
            files = [os.path.join(path, pattern%i) for i in fileids]
            self.detectors[k]['Filelist'] = files
