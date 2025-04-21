def concat_pdfs(folder,name):
    import os
    from PyPDF2 import PdfWriter

    merger = PdfWriter()
    files = os.listdir(folder)
    files.sort()
    for pdf in files:
        merger.append(folder+'/'+pdf)
    merger.write(folder+'/'+name+'.pdf')
    merger.close()