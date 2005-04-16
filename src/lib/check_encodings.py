import gtk
from gdebug import debug
import dialog_extras as de
from gettext import gettext as _

class CheckEncoding:

    """A class to read a file and guess the correct text encoding."""
    
    def __init__ (self, file, encodings=None):
        if encodings: self.encodings = encodings
        else:
            self.encodings = ['iso8859','ascii','latin_1','cp850','cp1252','utf-8',]
        self.all_encodings= ['ascii','cp037','cp424',
                        'cp437','cp500','cp737','cp775','cp850','cp852',
                        'cp855','cp856','cp857','cp860','cp861','cp862',
                        'cp863','cp864','cp865','cp869','cp874','cp875',
                        'cp1006','cp1026','cp1140','cp1250','cp1251',
                        'cp1252','cp1253','cp1254','cp1255','cp1256',
                        'cp1258','latin_1','iso8859_2','iso8859_3',
                        'iso8859_4','iso8859_5','iso8859_6','iso8859_7',
                        'iso8859_8','iso8859_9','iso8859_10','iso8859_13',
                        'iso8859_14','iso8859_15','koi8_r','koi8_u',
                        'mac_cyrillic','mac_greek','mac_iceland','mac_latin2',
                        'mac_roman','mac_turkish','utf_16','utf_16_be',
                        'utf_16_le','utf_7','utf_8']
        f = open(file,'r')
        self.txt = f.read()
        f.close()

    def test_encodings (self):
        """Move through self.encodings one at a time and return the first
        encoding that decodes our text cleanly. We return a tuple (encoding,decoded_text)"""
        for e in self.encodings:
            try:
                t=self.txt.decode(e)
                return (e,t)
            except UnicodeDecodeError:
                pass

    def get_encodings (self):
        encs = self.test_all_encodings(self.encodings)
        if encs:
            return encs
        else:
            return self.test_all_encodings(self.all_encodings)
            
    def test_all_encodings (self,encodings=None):
        """Test all encodings and return a dictionary of possible encodings."""
        if not encodings: encodings=self.all_encodings
        self.possible_encodings = {}
        for e in encodings:
            try:
                d=self.txt.decode(e)
                if not d in self.possible_encodings.values():
                    # if we don't already have this possibility, add 
                    self.possible_encodings[e]=d.encode('utf8')
            except UnicodeDecodeError:
                pass
        return self.possible_encodings

class GetFile (CheckEncoding):
    """Handed a filename, return a list of lines."""
    def __init__ (self,file,encodings=None):
        CheckEncoding.__init__(self,file,encodings)
        encs=self.get_encodings()
        if encs:
            if len(encs.keys()) > 1:
                encoding = getEncoding(encodings=encs)
            else:
                encoding = encs.keys()[0]
            self.enc = encoding
            self.lines = encs[self.enc].split('\n')            
            debug('reading file %s as encoding %s'%(file, self.enc))
            self.lines = map(lambda l: l.encode(),self.lines)
        else:
            raise "Cannot decode file %s"%file

def get_file (file, encodings=None):
    gf = GetFile(file, encodings)
    debug('returning lines %s,%s,%s'%(gf.lines[0],gf.lines[1],gf.lines[2]),0)
    return gf.lines

class EncodingDialog (de.optionDialog):
    def __init__ (self, default=None, label=_("Select encoding"),
                  sublabel=_("Cannot determine proper encoding. Please select the correct encoding from the following list."),
                  expander_label=_("See _file with encoding"),
                  encodings=[],
                 ):
        self.diff_lines = {}
        self.cursor_already_set = False
        self.expander_label=expander_label
        self.encodings = encodings
        self.current_error = 0
        self.diff_texts()
        options = self.create_options()
        expander=self.create_expander()
        self.setup_buffers()
        de.optionDialog.__init__(self, default=default,label=label, sublabel=sublabel,
                                 options=options, expander=expander)
        self.optionMenu.connect('activate',self.change_encoding)
        self.change_encoding()
        self.created = False

    def setup_motion_buttons (self):
        self.hbb = gtk.HButtonBox()
        self.fb = gtk.Button('Next Difference')
        self.pb = gtk.Button('Previous Difference')
        self.pb.connect('clicked',lambda *args: self.move_to_difference(forward=False))
        self.fb.connect('clicked',lambda *args: self.move_to_difference(forward=True))
        self.hbb.add(self.pb)
        self.hbb.add(self.fb)
        self.evb.add(self.hbb)
        self.hbb.show_all()

    def get_option (self,widget):
        de.optionDialog.get_option(self,widget)
        self.change_encoding()

    def create_options (self):
        return self.encodings.keys()

    def create_expander (self):
        self.evb = gtk.VBox()
        self.sw = gtk.ScrolledWindow()
        self.tv = gtk.TextView()
        self.tv.set_editable(False)
        self.buffer = self.tv.get_buffer()
        self.sw.add(self.tv)
        self.sw.show_all()
        self.evb.add(self.sw)
        #self.setup_motion_buttons() # doesn't work yet
        self.evb.show_all()
        return self.expander_label,self.evb
    
    def setup_buffers (self):
        self.encoding_buffers={}
        for k,t in self.encodings.items():
            self.encoding_buffers[k]=gtk.TextBuffer()
            self.highlight_tags = [self.encoding_buffers[k].create_tag(background='yellow')]
            self.line_highlight_tags = [self.encoding_buffers[k].create_tag(background='green')]
            self.set_buffer_text(self.encoding_buffers[k],t)

    def change_encoding (self):
        #self.buffer.set_text(self.encodings[self.ret])
        #self.set_buffer_text(self.encodings[self.ret])
        if self.cursor_already_set:
            im=self.buffer.get_insert()
            ti=self.buffer.get_iter_at_mark(im)
            offset=ti.get_offset()
        self.tv.set_buffer(self.encoding_buffers[self.ret])
        self.buffer = self.encoding_buffers[self.ret]
        debug('changed text to encoding %s'%self.ret,0)        
        #print 'fdl:',first_diffline,' fdc:',first_diffchar        
        
    def move_to_difference (self, forward=True):        
        dkeys = self.diff_lines.keys()
        dkeys.sort()
        if forward:
            self.current_error += 1
        else:
            self.current_error = self.current_error - 1
        if self.current_error > len(dkeys): self.current_error = 0
        if self.current_error < 0: self.current_error = len(dkeys)-1
        mark=self.buffer.create_mark(
            None,
            self.buffer.get_iter_at_line_index(dkeys[self.current_error],0),
            False,
            )
        print 'moving to %s'%dkeys[self.current_error]
        self.tv.scroll_to_mark(mark,0)

        
        
    def set_buffer_text (self, buffer, text):
        for n,l in enumerate(text.split('\n')):
            if n in self.diff_lines.keys():
                start = 0
                diffs = self.diff_lines[n]
                for sdiff,ediff in diffs:
                    buffer.insert_with_tags(buffer.get_end_iter(),l[start:sdiff],*self.line_highlight_tags)
                    buffer.insert_with_tags(buffer.get_end_iter(),l[sdiff:ediff],*self.highlight_tags)
                    start = ediff
                buffer.insert_with_tags(buffer.get_end_iter(),l[start:]+'\n',*self.line_highlight_tags)
            else:
                buffer.insert_with_tags(buffer.get_end_iter(),l+'\n')

    def diff_texts (self):
        """Look at our differently encoded buffers for characters where they differ."""
        encoded_buffers = self.encodings.values()
        enc1 = encoded_buffers[0]
        enc_rest = [e.split('\n') for e in encoded_buffers[1:]]
        for linenum, l in enumerate(enc1.split('\n')):
            other_lines = [len(e)>linenum and e[linenum] for e in enc_rest]
            if False in [l==ol for ol in other_lines]:
                ranges = []
                for chnum,ch in enumerate(l):
                    if False in [len(line)>ch and ch == line[chnum] for line in other_lines]:
                        if ranges and ranges[-1][1]==chnum:
                            ranges[-1][1]=chnum+1
                        else:
                            ranges.append([chnum,chnum+1])
                self.diff_lines[linenum]=ranges
                
        
def getEncoding (*args,**kwargs):
    d=EncodingDialog(*args,**kwargs)
    return d.run()

if __name__ == '__main__':
    print 'grabbing dialog extras'
    import dialog_extras as de
    print 'selecting file'
    fn=de.select_file('Select file to decode',filters=[['Plain Text',['text/plain'],'*txt']],)
    print 'fn = ',fn
    print "Got file ", get_file(fn)[0:5]
