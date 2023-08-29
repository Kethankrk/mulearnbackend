from itertools import islice
from rest_framework.views import APIView

from db.task import TotalKarma

from . import dash_zonal_helper
from db.organization import District, Organization, UserOrganizationLink
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType
from utils.utils import CommonUtils

from . import dash_zonal_serializer
from django.db.models import Sum, F
from django.db.models import (
    F,
    ExpressionWrapper,
    CharField,
    Value,
    Case,
    When,
    IntegerField,
)


class ZonalDetailsAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ZONAL_CAMPUS_LEAD.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user_org_link = dash_zonal_helper.get_user_college_link(user_id)
        serializer = dash_zonal_serializer.ZonalDetailsSerializer(
            user_org_link, many=False
        )
        return CustomResponse(response=serializer.data).get_success_response()


class ZonalTopThreeDistrictAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ZONAL_CAMPUS_LEAD.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user_org_link = dash_zonal_helper.get_user_college_link(user_id)

        district_karma_dict = (
            UserOrganizationLink.objects.filter(
                org__district__zone=user_org_link.org.district.zone,
                verified=True,
            )
            .values("org__district")
            .annotate(total_karma=Sum("user__total_karma_user__karma"))
        )

        district_ranks = {
            data["org__district"]: data["total_karma"]
            if data["total_karma"] is not None
            else 0
            for data in district_karma_dict
        }

        district_ranks = dict(
            sorted(district_ranks.items(), key=lambda x: x[1], reverse=True)
        )

        top_districts = dict(islice(district_ranks.items(), 3))

        org_user_district = District.objects.filter(id__in=top_districts).distinct()

        serializer = dash_zonal_serializer.ZonalTopThreeDistrictSerializer(
            org_user_district, many=True, context={"ranks": district_ranks}
        )

        return CustomResponse(response=serializer.data).get_success_response()


class ZonalStudentLevelStatusAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ZONAL_CAMPUS_LEAD.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = dash_zonal_helper.get_user_college_link(user_id)
        district_id = user_org_link.org.district.id

        org = Organization.objects.filter(
            district__id=district_id, org_type=OrganizationType.COLLEGE.value
        )

        serializer = dash_zonal_serializer.ZonalStudentLevelStatusSerializer(
            org, many=True
        )
        return CustomResponse(response=serializer.data).get_success_response()


class ZonalStudentDetailsAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ZONAL_CAMPUS_LEAD.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user_org_link = dash_zonal_helper.get_user_college_link(user_id)

        user_org_links = UserOrganizationLink.objects.filter(
            org__district__zone=user_org_link.org.district.zone,
            org__org_type=OrganizationType.COLLEGE.value,
        )

        paginated_queryset = CommonUtils.get_paginated_queryset(
            user_org_links,
            request,
            ["user__first_name"],
            {
                "name": "user__full_name",
                "muid": "user__mu_id",
                "karma": "user__total_karma_user__karma",
                "level": "user__user_level_link_user__level__level_order",
            },
        )

        serializer = dash_zonal_serializer.ZonalStudentDetailsSerializer(
            paginated_queryset.get("queryset"), many=True
        ).data

        return CustomResponse(
            response={
                "data": serializer,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()


class ZonalStudentDetailsCSVAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ZONAL_CAMPUS_LEAD.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org_link = dash_zonal_helper.get_user_college_link(user_id)

        user_org_links = UserOrganizationLink.objects.filter(
            org__district__zone=user_org_link.org.district.zone,
            org__org_type=OrganizationType.COLLEGE.value,
        )

        serializer = dash_zonal_serializer.ZonalStudentDetailsSerializer(
            user_org_links, many=True
        )
        return CommonUtils.generate_csv(serializer.data, "Zonal Details")


class ListAllDistrictsAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ZONAL_CAMPUS_LEAD.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org = Organization.objects.filter(
            user_organization_link_org_id__user_id=user_id,
            org_type=OrganizationType.COLLEGE.value,
        ).first()

        organizations = Organization.objects.filter(
            district__zone=user_org.district.zone,
            org_type=OrganizationType.COLLEGE.value,
        )

        paginated_queryset = CommonUtils.get_paginated_queryset(
            organizations,
            request,
            [
                "title",
                "code",
                "user_organization_link_org_id__user__first_name",
                "user_organization_link_org_id__user__mobile",
            ],
            {
                "title": "title",
                "code": "code",
                "lead": "user_organization_link_org_id__user__first_name",
                "mobile": "user_organization_link_org_id__user__mobile",
            },
        )

        serializer = dash_zonal_serializer.ListAllDistrictsSerializer(
            paginated_queryset.get("queryset"), many=True
        ).data

        return CustomResponse(
            response={
                "data": serializer,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()


class ListAllDistrictsCSVAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ZONAL_CAMPUS_LEAD.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_org = Organization.objects.filter(
            user_organization_link_org_id__user_id=user_id,
            org_type=OrganizationType.COLLEGE.value,
        ).first()

        organizations = Organization.objects.filter(
            district_zone=user_org.district.zone,
            org_type=OrganizationType.COLLEGE.value,
        )

        serializer = dash_zonal_serializer.ListAllDistrictsSerializer(
            organizations, many=True
        )
        return CommonUtils.generate_csv(serializer.data, "District Details")
