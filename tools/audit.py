import discord
from tools.discord_search import SearchTools

RECENT_AUDITS = {}


#AuditDaata: data to store when retrieving an entry from the audit log
class AuditData():
    def __init__(self, del_count: int, bulk_del_count: int):
        self.del_count = del_count
        self.bulk_del_count = bulk_del_count


# Audits: saves most recent audits entry data
class Audits():
    def __init__(self, client: discord.Client):
        self.client = client

    # get_recent_audit() Gets all the recent delete audit entries of every guild
    async def get_recent_audit(self):
        for guild in self.client.guilds:
            del_audit = await SearchTools.get_recent_audit(guild, None, action = discord.AuditLogAction.message_delete)
            bulk_del_audit = await SearchTools.get_recent_audit(guild, None, action = discord.AuditLogAction.message_bulk_delete)


            if (del_audit is None):
                del_audit_count = 0
            else:
                del_audit_count = del_audit.extra.count

            if (bulk_del_audit is None):
                bulk_del_audit_count = 0
            else:
                bulk_del_audit_count = bulk_del_audit.extra["count"]

            RECENT_AUDITS[guild.id] = AuditData(del_audit_count, bulk_del_audit_count)
