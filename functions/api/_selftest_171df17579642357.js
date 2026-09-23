import { rowId, nowMs } from "../_lib/db.js";

function j(data,status=200){
  return new Response(JSON.stringify(data),{
    status,
    headers:{"content-type":"application/json; charset=utf-8","cache-control":"no-store"}
  });
}

async function sha256(text){
  const bytes=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(text));
  return [...new Uint8Array(bytes)].map(x=>x.toString(16).padStart(2,"0")).join("");
}

export async function onRequestGet(context){
  const db=context.env.DB;
  if(!db) return j({ok:false,error:"db_missing"},500);

  const base=new URL(context.request.url).origin;
  const stamp=Date.now();
  const inquiryMarker="SELFTEST-INQ-"+stamp;
  const businessMarker="SELFTEST-BIZ-"+stamp;
  const results={startedAt:new Date().toISOString()};

  let inquiryId=null,businessId=null,setupAdId=null,tempApprovedId=null;

  try{
    // 1) Inquiry public API -> D1
    const ir=await fetch(base+"/api/inquiry",{
      method:"POST",
      headers:{"content-type":"application/json","Origin":"https://fukuoka-ihinseiri-guide.com"},
      body:JSON.stringify({
        name:inquiryMarker,
        phone:"000-0000-0000",
        email:"selftest@example.com",
        region:"SELFTEST",
        serviceType:"遺品整理",
        floorPlan:"TEST",
        budget:"TEST",
        preferredTiming:"TEST",
        details:"Automated production self-test"
      })
    });
    const ij=await ir.json().catch(()=>({}));
    inquiryId=ij.id||null;
    const inquiryRow=inquiryId?await db.prepare("SELECT id,name,status FROM inquiries WHERE id=?").bind(inquiryId).first():null;
    results.inquiry={
      http:ir.status,
      apiOk:Boolean(ij.ok),
      persisted:Boolean(inquiryRow&&inquiryRow.name===inquiryMarker&&inquiryRow.status==="未対応")
    };

    // 2) Business public API -> D1
    const br=await fetch(base+"/api/business",{
      method:"POST",
      headers:{"content-type":"application/json","Origin":"https://fukuoka-ihinseiri-guide.com"},
      body:JSON.stringify({
        companyName:businessMarker,
        contactPerson:"SELFTEST",
        phone:"000-0000-0000",
        email:"selftest@example.com",
        serviceArea:"SELFTEST",
        serviceContent:"遺品整理"
      })
    });
    const bj=await br.json().catch(()=>({}));
    businessId=bj.id||null;
    const businessRow=businessId?await db.prepare("SELECT id,company_name,status FROM business_applications WHERE id=?").bind(businessId).first():null;
    results.business={
      http:br.status,
      apiOk:Boolean(bj.ok),
      persisted:Boolean(businessRow&&businessRow.company_name===businessMarker&&businessRow.status==="未対応")
    };

    // 3) Approved business setup token -> advertisement creation
    tempApprovedId=rowId("selfbiz");
    const token="selftest-token-"+stamp;
    const hash=await sha256(token);
    const now=nowMs();
    await db.prepare(`INSERT INTO business_applications
      (id,company_name,contact_person,phone,email,service_area,service_content,status,setup_token_hash,setup_token_created_at,setup_token_expires_at,created_at,updated_at)
      VALUES (?,?,?,?,?,?,?,'承認',?,?,?,?,?)`)
      .bind(tempApprovedId,"SELFTEST-ADVERTISER","SELFTEST","000-0000-0000","selftest@example.com","SELFTEST","遺品整理",hash,now,now+3600000,now,now).run();

    const sr=await fetch(base+"/api/business/setup/"+encodeURIComponent(token),{
      method:"POST",
      headers:{"content-type":"application/json","Origin":"https://fukuoka-ihinseiri-guide.com"},
      body:JSON.stringify({
        catchphrase:"SELFTEST",
        description:"Automated production self-test",
        phone:"000-0000-0000",
        email:"selftest@example.com",
        priceRange:"TEST",
        businessHours:"TEST",
        websiteUrl:"https://example.com/",
        qualifications:"TEST",
        serviceArea:"SELFTEST",
        serviceGenres:["遺品整理"]
      })
    });
    const sj=await sr.json().catch(()=>({}));
    const ad=await db.prepare("SELECT id,placements_json,website_url,is_active FROM advertisements WHERE business_id=?").bind(tempApprovedId).first();
    setupAdId=ad?.id||null;
    results.adSetup={
      http:sr.status,
      apiOk:Boolean(sj.ok),
      created:Boolean(ad),
      defaultPlacement:ad?.placements_json||null,
      websiteUrl:ad?.website_url||null,
      inactiveByDefault:Number(ad?.is_active||0)===0
    };

    // 4) Ad inventory API and empty serve state
    const pr=await fetch(base+"/api/ad/placements",{headers:{"Origin":"https://fukuoka-ihinseiri-guide.com"}});
    const pj=await pr.json().catch(()=>({}));
    const ar=await fetch(base+"/api/ad/serve?genre="+encodeURIComponent("遺品整理")+"&placement=article_middle",{headers:{"Origin":"https://fukuoka-ihinseiri-guide.com"}});
    const aj=await ar.json().catch(()=>({}));
    results.adInventory={
      pricingHttp:pr.status,
      pricingApiOk:Boolean(pj.ok),
      activePublicPlacements:Array.isArray(pj.placements)?pj.placements.length:null,
      serveHttp:ar.status,
      noActiveAd:aj.ad===null
    };

    // 5) Security: foreign browser Origin must be rejected
    const xr=await fetch(base+"/api/inquiry",{
      method:"POST",
      headers:{"content-type":"application/json","Origin":"https://example.invalid"},
      body:JSON.stringify({
        name:"BLOCK-ME",phone:"000",email:"selftest@example.com",region:"TEST",serviceType:"TEST"
      })
    });
    const xj=await xr.json().catch(()=>({}));
    results.originGuard={
      http:xr.status,
      rejected:xr.status===403&&xj.error==="origin_not_allowed"
    };

    results.ok=[
      results.inquiry.http===200,results.inquiry.apiOk,results.inquiry.persisted,
      results.business.http===200,results.business.apiOk,results.business.persisted,
      results.adSetup.http===200,results.adSetup.apiOk,results.adSetup.created,
      results.adSetup.defaultPlacement==='["article_middle"]',
      results.adSetup.websiteUrl==="https://example.com/",
      results.adSetup.inactiveByDefault,
      results.adInventory.pricingHttp===200,results.adInventory.pricingApiOk,
      results.adInventory.serveHttp===200,results.adInventory.noActiveAd,
      results.originGuard.rejected
    ].every(Boolean);
  }catch(e){
    results.ok=false;
    results.error=String(e?.message||e);
  }finally{
    // Cleanup all synthetic business/ad/inquiry rows.
    try{if(setupAdId)await db.prepare("DELETE FROM advertisements WHERE id=?").bind(setupAdId).run();}catch{}
    try{if(tempApprovedId)await db.prepare("DELETE FROM business_applications WHERE id=?").bind(tempApprovedId).run();}catch{}
    try{if(businessId)await db.prepare("DELETE FROM business_applications WHERE id=?").bind(businessId).run();}catch{}
    try{if(inquiryId)await db.prepare("DELETE FROM inquiries WHERE id=?").bind(inquiryId).run();}catch{}

    // Verify cleanup.
    try{
      const left=await db.prepare(
        "SELECT (SELECT COUNT(*) FROM inquiries WHERE name LIKE 'SELFTEST-%') inquiry_count, "+
        "(SELECT COUNT(*) FROM business_applications WHERE company_name LIKE 'SELFTEST-%') business_count, "+
        "(SELECT COUNT(*) FROM advertisements WHERE company_name LIKE 'SELFTEST-%') ad_count"
      ).first();
      results.cleanup={
        inquiries:Number(left?.inquiry_count||0),
        businesses:Number(left?.business_count||0),
        ads:Number(left?.ad_count||0),
        clean:Number(left?.inquiry_count||0)===0&&Number(left?.business_count||0)===0&&Number(left?.ad_count||0)===0
      };
      results.ok=Boolean(results.ok&&results.cleanup.clean);
    }catch(e){
      results.cleanup={clean:false,error:String(e?.message||e)};
      results.ok=false;
    }
    results.finishedAt=new Date().toISOString();
  }

  return j(results,results.ok?200:500);
}
