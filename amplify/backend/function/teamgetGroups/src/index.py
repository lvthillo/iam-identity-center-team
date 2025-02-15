# © 2023 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
# This AWS Content is provided subject to the terms of the AWS Customer Agreement available at
# http: // aws.amazon.com/agreement or other written agreement between Customer and either
# Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
import os
from botocore.exceptions import ClientError
import boto3

user_pool_id = os.getenv("AUTH_AWSPIM06DBB7FC_USERPOOLID")
team_admin_group = os.getenv("TEAM_ADMIN_GROUP")
team_auditor_group = os.getenv("TEAM_AUDITOR_GROUP")

def add_user_to_group(username, groupname):
    client = boto3.client('cognito-idp')
    try:
        response = client.admin_add_user_to_group(
            UserPoolId=user_pool_id,
            Username=username,
            GroupName=groupname
        )
        print(f"user {username} added to {groupname} group")
    except ClientError as e:
        print(e.response['Error']['Message'])


def remove_user_from_group(username, groupname):
    client = boto3.client('cognito-idp')
    try:
        response = client.admin_remove_user_from_group(
            UserPoolId=user_pool_id,
            Username=username,
            GroupName=groupname
        )
        print(f"user {username} removed from {groupname} group")
    except ClientError as e:
        print(e.response['Error']['Message'])


def get_identiy_store_id():
    client = boto3.client('sso-admin')
    try:
        response = client.list_instances()
        return response['Instances'][0]['IdentityStoreId']
    except ClientError as e:
        print(e.response['Error']['Message'])


sso_instance = get_identiy_store_id()


def get_user(username):
    try:
        client = boto3.client('identitystore')
        response = client.list_users(
            IdentityStoreId=sso_instance,
            Filters=[
                {
                    'AttributePath': 'UserName',
                    'AttributeValue': username
                },
            ]
        )
        return response['Users'][0]['UserId']
    except ClientError as e:
        print(e.response['Error']['Message'])


def get_group(group):
    try:
        client = boto3.client('identitystore')
        response = client.get_group_id(
            IdentityStoreId=sso_instance,
            AlternateIdentifier={
                'UniqueAttribute': {
                    'AttributePath': 'DisplayName',
                    'AttributeValue': group
                }
            }
        )
        return response['GroupId']
    except ClientError as e:
        print(e.response['Error']['Message'])

# Paginate

def list_idc_group_membership(userId):
    try:
        client = boto3.client('identitystore')
        p = client.get_paginator('list_group_memberships_for_member')
        paginator = p.paginate(IdentityStoreId=sso_instance,
            MemberId={
                'UserId': userId
            })
        all_groups = []
        for page in paginator:
            all_groups.extend(page["GroupMemberships"])
        return all_groups
    except ClientError as e:
        print(e.response['Error']['Message'])


def handler(event, context):
    print(event)
    user = event["identity"]["username"]
    # Strip idc prefix
    username = user.removeprefix("idc_")
    userId = get_user(username)
    admin = get_group(team_admin_group)
    auditor = get_group(team_auditor_group)
    groups = []
    groupIds = []

    groupData = list_idc_group_membership(userId)

    for group in groupData:
        groupIds.append(group["GroupId"])
        if group['GroupId'] == admin:
            add_user_to_group(user, "Admin")
            groups.append("Admin")
        elif group['GroupId'] == auditor:
            add_user_to_group(user, "Auditors")
            groups.append("Auditors")

    if "Admin" not in groups:
        remove_user_from_group(user, "Admin")
    elif "Auditors" not in groups:
        remove_user_from_group(user, "Auditors")

    return {"groups": groups, "userId": userId, "groupIds": groupIds}