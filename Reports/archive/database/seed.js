// DEPRECATED: Do not use for production deployments.
// The authoritative source of truth for all database seeds is backend/scripts/seed_all.py.
// Run in a development database first.
const now = new Date();
[
 {code:"basic",name:"Basic",pricePerHourMinor:NumberLong(99900),features:["AC room","Birthday decoration theme","Music"]},
 {code:"gold",name:"Gold",pricePerHourMinor:NumberLong(150000),features:["Everything in Basic","Half-kg cake","Customized name letters","Welcome board"]},
 {code:"diamond",name:"Diamond",pricePerHourMinor:NumberLong(250000),features:["Everything in Gold","Bubble entry","Fog entry","One cold-fire gun"]}
].forEach(p=>db.packages.updateOne({code:p.code},{$set:{...p,currency:"INR",active:true,updatedAt:now},$setOnInsert:{createdAt:now}},{upsert:true}));
print("Package seed complete.");
