

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
    


import numpy as np
from dateutil.parser import parse
import os
import json
class fioFile():
    def __init__(self, fiofile, nodata='NAN'):
        self.fiofile = fiofile
        self.path = os.path.realpath(self.fiofile).partition('/raw/')[0]
        self.nodata = nodata
        self.sweepType = None
        self._fioparser(fn=self.fiofile)
        self.allFilesExist = False
        if self.sweepType is not None:
            self._gen_file_list()
            self._check_files_exist()
            if self.allFilesExist:
                self._gen_image_file_positions()
        print(f"Sweep type: {self.sweepType}")
        
    def __str__(self):
        return '''Python object holding a parsed fio file.
        In the case of a sweep fio file the class generates all corresponding file names (for all detectors used in the sweep) and checks if they exist.
        If the scan was a sweep and all files exist, a dictionary containing the sweep and outer (if any) encoder positions is created. This can then be queried via the get_pos method either giving it a filename or an index, which represents the N-th step in the sweep.
        If other motor/encoder positions are also required (id the dictionary returned by the get_pos method) the dictionary may be recreated with the _gen_image_file_positions method, which accepts a keyword option called extramots=[], where one can give in additional motor names.
        
        '''

    def _get_asap3_path(self):
        '''
        get the data path from the core system
        '''
        if os.path.realpah(self.fiofile).startswith('/asap3/'):
            return os.path.realpah(self.fiofile).partition('/raw/')[0]
        elif os.path.realpath(self.fiofile).startswith('/gpfs/'):
            metaFile = [x for x in  os.listdir('/gpfs/current/') if x.enswith('.json')][0]
            return json.load(open(os.path.join('/gpfs/current/', metaFile)))['corePath']
        
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
            self.sweepType = self.command.split(" ")[0][:-6]  # fast, super or time
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

    def _gen_file_list(self):  # only if sweep
        for k,v in self.detectors.items():
            path = v['Filedir']
            realpath = os.path.join(self.path, 'raw', path.partition('/raw/')[2])
            pattern = v['Filepattern'].strip(" ")
            extension = pattern.rpartition(".")[2]
            if extension in ['cbf', 'tif']:
                fileids = [int(i) for i in self.data[k]]
            elif extension in ['hdf', 'nxs']:
                fileids = [1]  # TODO: handle hdf files from Varex and Manta as well as from the Eiger
            files = [os.path.join(realpath, pattern%i) for i in fileids]
            self.detectors[k]['Filelist'] = files
    
    def _check_files_exist(self, verbose=True):  # only if sweep
        success = True
        for k,v in self.detectors.items():
            c = 0
            for f in v['Filelist']:
                try:
                    assert os.path.exists(f), f"No such file: {f}"
                    c += 1
                except AssertionError as AE:
                    print(AE)
                    success = False
            if verbose:
                print(f"Detector {k}: found {c} files of {len(v['Filelist'])}")
        if success:
            self.allFilesExist = True
    
    def _gen_image_file_positions(self, extramots=[], verbose=True):  # only if sweep
        if self.sweepType == 'super':
            outer_axis = self.command.split(' ')[1]
            outer_axis_poss = self.data[list(self.data.keys())[2]]
        if self.sweepType in ['super', 'fast']:
            sweep_axis_poss = [(i+j)/2 for (i,j) in zip(self.data[list(self.data.keys())[0]], self.data[list(self.data.keys())[1]])]
            if self.sweepType == 'super':
                sweep_axis = self.command.split(' ')[5]
            elif self.sweepType == 'fast':
                sweep_axis = self.command.split(' ')[1]
        extrapos = []
        for e in extramots:
            if e in self.data.keys():
                extrapos.append(self.data[e])
                if verbose:
                    print(f"{e} motor positions added from the encoded motros, i.e. real measured motor position")
            elif e in self.parameterdict.keys():
                extrapos.append([self.parameterdict[e] for _ in range(len(self.data[list(self.data.keys())[0]]))])
                if verbose:
                    print(f"{e} motor positions added from the parameters list, i.e. motor position at the start of the scan")
            else:
                if verbose:
                    print(f"{e} motor positions could not be added")
        self.image_file_positions = {}
        for k,v in self.detectors.items():
            self.image_file_positions[k] = v['Filelist']
        if self.sweepType == 'super':
            self.image_file_positions[outer_axis] = outer_axis_poss
            self.image_file_positions[sweep_axis] = sweep_axis_poss
        if self.sweepType == 'fast':
            self.image_file_positions[sweep_axis] = sweep_axis_poss
        if extrapos != []:
            for name,pos in zip(extramots, extrapos):
                self.image_file_positions[name] = pos
    
    def get_pos(self, ident):
        '''
        ident is either a file name or the sequence number (iden-th image of the sweep)
        '''
        if isinstance(ident, str):
            asap3path = os.path.realpath(self.fiofile).partition('/raw/')[0]
            realpath = os.path.join(asap3path, 'raw', ident.partition('/raw/')[2])
            
            imfile = os.path.realpath(ident)
            for k in self.detectors.keys():
                for i,n in enumerate(self.image_file_positions[k]):
                    if imfile == n:
                        dct = {}
                        dct['index'] = i
                        #dct['name'] = imfile
                        for kk,v in self.image_file_positions.items():
                            dct[kk] = v[i]
                        return dct
            else:
                raise ValueError(f"{imfile} is not in the list of any of the detectors used in this scan")
        elif isinstance(ident, int):
            assert ident < len(self.data[list(self.data.keys())[0]]), f"index {ident} is out of range ({len(self.data[list(self.data.keys())[0]])})"
            for k in self.detectors.keys():
                dct = {}
                dct['index'] = ident
                for k,v in self.image_file_positions.items():
                    dct[k] = v[ident]
                return dct
