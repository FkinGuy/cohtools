#!/usr/bin/python
import sys, os, errno, struct, datetime, zlib, optparse
import hashlib

def is_match(name, args):
  if len(args) == 0:
    return True
  # FIXME: handle wildcards?
  return name in args

class DirEntry(object):
  def __init__(self, dirent):
    self.name = None
    self.slot = None
    self.strnum = dirent[1]
    self.fsize = dirent[2]
    self.tstamp = datetime.datetime.fromtimestamp(dirent[3])
    self.offset = dirent[4]
    self.slotnum = dirent[6]
    self.md5 = dirent[7]
    self.csize = dirent[8]

class PiggFile(object):
  def __init__(self, fname):
    self.fname = fname
    self.files = []
    self.strings = []
    self.slots = []
    self.hdr = []

    self.f = open(fname+".pigg", "wb")
    #lire arborescence
    liste_fichiers = []
    for dossier, sous_dossiers, fichiers in os.walk(fname):
      for fichier in fichiers:
        liste_fichiers.append(os.path.join(dossier, fichier))

    self.hdr_pack=struct.pack("<LHHHHL", 291, 2, 2, 16, 48, len(liste_fichiers) )
    self.f.write(self.hdr_pack)

    pos = self.f.tell()
    print "fin hdr:",pos

    #print (liste_fichiers)
    dico_fichiers={}
    for fichier in liste_fichiers:
      fsize = os.path.getsize(fichier)
      fichier_data = open(fichier,"rb").read()
      if fsize != len(fichier_data):
        pass
        """
        print "erreur de taille"
        print "fsize=",str(fsize)
        print "len(fichier_data)=", str(len(fichier_data))
        """
      fmd5 = hashlib.md5(fichier_data).hexdigest()
      name = fichier

      slot = None
      slotnum = long(0)
      strnum = 0
      ftstamp = os.path.getmtime(fichier)

      fichier_data_z = zlib.compress(fichier_data)
      csize = len(fichier_data_z)
      offset = pos + csize
      fichier_temp = os.path.join(os.environ["TEMP"], "writepigg", fichier)
      if not os.path.exists(os.path.dirname(fichier_temp)):
        os.makedirs(os.path.dirname(fichier_temp))
      open(fichier_temp, "wb").write(fichier_data_z)
      dico_fichiers[fichier] = [0, strnum, fsize, ftstamp, offset, 0, slotnum, fmd5, csize]
      self.files_pack = struct.pack("<LLLLLLL16sL", 0, strnum, fsize, ftstamp, offset, 0, slotnum, fmd5, csize)
      self.f.write(self.files_pack)
      pos=self.f.tell()
      print "fin ecriture dir fichier et csize ", fichier, pos, csize
    #print dico_fichiers

    pos = self.f.tell()
    print "fin directories:",pos

    offset_strhdr = pos
    self.strhdr_pack = struct.pack("<LLL", 0x6789, len(liste_fichiers), 0 )
    self.f.write(self.strhdr_pack)

    pos = self.f.tell()
    print "fin header_liste_fichiers:",pos


    self.strings_pack = ""
    for fichier in liste_fichiers:
      taille= len(fichier)+1
      self.f.write(struct.pack("<L", taille))
      self.f.write(fichier)
      self.f.write(chr(0))
    pos = self.f.tell()
    print "fin liste_fichiers:",pos
    offset_fin_liste_fichiers = pos

    self.slothdr_pack = struct.pack("<LLL", 0x9abc, 0, 0 )
    self.f.write(self.slothdr_pack)
    pos = self.f.tell()
    print "fin slot hdr:",pos

    liste_offsets = []
    for fichier in liste_fichiers:
      fichier_temp = os.path.join(os.environ["TEMP"], "writepigg", fichier)
      csize = dico_fichiers[fichier][8]
      self.f.write(struct.pack("<L",csize))
      liste_offsets.append(self.f.tell())
      fichier_data_z = open(fichier_temp,"rb").read()
      mycsize = len (fichier_data_z)
      self.f.write(fichier_data_z)
      toto=zlib.decompress(fichier_data_z)
      pos=self.f.tell()
      print "fin fichier",fichier, pos, csize, mycsize


    self.f.seek(offset_strhdr)
    self.strhdr_pack = struct.pack("<LLL", 0x6789, len(liste_fichiers), offset_fin_liste_fichiers - offset_strhdr - 12 )
    self.f.write(self.strhdr_pack)

    self.f.close()

    self.f = open(fname+".pigg", "r+")

    self.f.seek(16)

    i=0
    for fichier in liste_fichiers:
      #dico_fichiers[fichier] = [0, strnum, fsize, ftstamp, offset, 0, slotnum, fmd5, csize]
      info1 = dico_fichiers[fichier][0]
      strnum = dico_fichiers[fichier][1]
      fsize = dico_fichiers[fichier][2]
      ftstamp = dico_fichiers[fichier][3]
      offset = liste_offsets[i]
      info2 = dico_fichiers[fichier][5]
      slotnum = dico_fichiers[fichier][6]
      fmd5 = dico_fichiers[fichier][7]
      csize = dico_fichiers[fichier][8]
      print repr(offset)
      self.files_pack = struct.pack("<LLLLLLL16sL", info1, strnum, fsize, ftstamp, offset, info2, slotnum, fmd5, csize)
      self.f.write(self.files_pack)
      pos = self.f.tell()
      print "fin reecriture fichier et csize", fichier, pos, csize
      i += 1

    print "liste_offsets=",liste_offsets
    sys.exit(0)


  def list_files(self, args, options):
    print " Length     Size    Meta      Date   Time               MD5                  Name"
    print "--------  -------  -----  ---------- ----- --------------------------------  ----"
    for ent in self.files:
      if not is_match(ent.name, args):
        continue
      name = ent.name
      fsize = ent.fsize
      csize = ent.csize
      if csize == 0:
        csize = fsize
      if ent.slot is not None:
        msize = len(ent.slot)
      else:
        msize = 0
      dt = ent.tstamp.strftime("%Y-%m-%d %H:%M")
      md5 = "".join(["%02x" % ord(x) for x in ent.md5])
      print "%8u %8u %6u  %s %s  %s" % (fsize, csize, msize, dt, md5, name)

  def extract_files(self, args, options):
    for ent in self.files:
      if not is_match(ent.name, args):
        continue
      name = ent.name
      if not options.quiet and not options.pipe:
        print "Extracting %s..." % name
      self.f.seek(ent.offset)
      if ent.csize == 0:
        data = self.f.read(ent.fsize)
      else:
        cdata = self.f.read(ent.csize)
        data = zlib.decompress(cdata)
      if options.pipe:
        sys.stdout.write(data)
        sys.stdout.flush()
      else:
        try:
          os.makedirs(os.path.dirname(name))
        except OSError, e:
          if e.errno != errno.EEXIST:
            raise
        df = open(name, "wb")
        df.write(data)
        df.close()

  def extract_meta(self, args, options):
    for ent in self.files:
      if ent.slot is None:
        continue
      if not is_match(ent.name, args):
        continue
      name = ent.name + ".meta"
      if not options.quiet and not options.pipe:
        print "Extracting %s..." % name
      data = ent.slot
      if options.pipe:
        sys.stdout.write(data)
        sys.stdout.flush()
      else:
        try:
          os.makedirs(os.path.dirname(name))
        except OSError, e:
          if e.errno != errno.EEXIST:
            raise
        df = open(name, "wb")
        df.write(data)
        df.close()

  def decompress_slot(self, data):
    fsize = struct.unpack("<L", data[:4])[0]
    if fsize == len(data):
      return data[4:]
    (fsize, csize) = struct.unpack("<LL", data[:8])
    if fsize + 4 != len(data):
      print "Slot size mismatch:", fsize, csize, len(data)
    if csize == 0:
      return data[8:]
    else:
      return zlib.decompress(data[8:])

  def read_struct(self, format, size):
    if size is None:
      size = struct.calcsize(format)
    data = self.f.read(size)
    return struct.unpack(format, data)

  def read_vardata(self):
    slen = self.read_struct("<L", 4)[0]
    data = self.f.read(slen)
    return data

  def read_string(self):
    # strip final null byte
    return self.read_vardata()[:-1]

def main():

  usage = "usage: %prog [options] file.pigg [filenames]"
  parser = optparse.OptionParser(usage=usage)
  parser.add_option("-l", "--list",
                    action="store_true", dest="list_files",
                    help="list contents of PIGG")
  parser.add_option("-m", "--meta",
                    action="store_true", dest="meta",
                    help="extract metadata")
  parser.add_option("-p", "--pipe",
                    action="store_true", dest="pipe",
                    help="extract to standard output")
  parser.add_option("-q", "--quiet",
                    action="store_true", dest="quiet",
                    help="quiet mode")

  (options, args) = parser.parse_args()

  if len(args) < 1:
    parser.error("need a filename")

  f = PiggFile(args[0])
  if options.list_files:
    f.list_files(args[1:], options)
  elif options.meta:
    f.extract_meta(args[1:], options)
  else:
    f.extract_files(args[1:], options)

if __name__ == "__main__":
  main()
