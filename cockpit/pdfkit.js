ObjC.import('Foundation')
ObjC.import('PDFKit')

function run(paths) {
  const doc = $.PDFDocument.alloc.initWithURL($.NSURL.fileURLWithPath(paths[0]))
  let pages = []
  for (let index = 0; index < Math.min(doc.pageCount, 12); index++) {
    pages.push(ObjC.unwrap(doc.pageAtIndex(index).string) || '')
  }
  return pages.join('\n')
}
